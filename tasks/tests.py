from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project, ProjectMembership

from .forms import TaskForm
from .models import Task

PASSWORD = 'Str0ngPass!234'


class TaskTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.localdate()
        cls.today = today
        cls.manager = User.objects.create_user('manager', 'm@example.com', PASSWORD)
        cls.member = User.objects.create_user('member', 'mem@example.com', PASSWORD)
        cls.other = User.objects.create_user('other', 'oth@example.com', PASSWORD)
        cls.outsider = User.objects.create_user('outsider', 'o@example.com', PASSWORD)

        cls.project = Project.objects.create(
            name='Alpha', start_date=today - timedelta(days=10),
            deadline=today + timedelta(days=30), created_by=cls.manager)
        ProjectMembership.objects.create(project=cls.project, user=cls.manager, role='manager')
        ProjectMembership.objects.create(project=cls.project, user=cls.member, role='member')
        ProjectMembership.objects.create(project=cls.project, user=cls.other, role='member')

        def make(title, user, priority='medium', status='todo', days=5, project=cls.project):
            return Task.objects.create(
                project=project, title=title, assigned_to=user, priority=priority,
                status=status, deadline=today + timedelta(days=days), created_by=cls.manager)

        cls.t_high = make('Write report', cls.member, priority='high')
        cls.t_low = make('Fix bug', cls.member, priority='low')
        cls.t_manager = make('Design logo', cls.manager)

        secret = Project.objects.create(
            name='Secret', start_date=today, deadline=today + timedelta(days=9),
            created_by=cls.outsider)
        ProjectMembership.objects.create(project=secret, user=cls.outsider, role='manager')
        cls.t_secret = make('Secret task', cls.outsider, project=secret)

    def login(self, username):
        self.assertTrue(self.client.login(username=username, password=PASSWORD))

    def titles(self, response):
        return [t.title for t in response.context['page']]


class TaskModelTests(TaskTestBase):
    def test_overdue_logic(self):
        late = Task.objects.create(project=self.project, title='Late', status='todo',
                                   deadline=self.today - timedelta(days=1), created_by=self.manager)
        self.assertTrue(late.is_overdue)
        late.status = 'completed'
        self.assertFalse(late.is_overdue)
        self.assertFalse(self.t_high.is_overdue)

    def test_deleting_assignee_keeps_task(self):
        self.member.delete()
        self.t_high.refresh_from_db()
        self.assertIsNone(self.t_high.assigned_to)


class TaskFormTests(TaskTestBase):
    def data(self, **extra):
        data = {
            'title': 'New task', 'description': '', 'assigned_to': self.member.pk,
            'priority': 'high', 'status': 'todo',
            'deadline': self.today + timedelta(days=3),
        }
        data.update(extra)
        return data

    def test_valid_form(self):
        self.assertTrue(TaskForm(self.data(), project=self.project).is_valid())

    def test_cannot_assign_to_non_member(self):
        form = TaskForm(self.data(assigned_to=self.outsider.pk), project=self.project)
        self.assertFalse(form.is_valid())
        self.assertIn('assigned_to', form.errors)

    def test_deadline_after_project_deadline_rejected(self):
        late = self.project.deadline + timedelta(days=1)
        form = TaskForm(self.data(deadline=late), project=self.project)
        self.assertFalse(form.is_valid())
        self.assertIn('deadline', form.errors)

    def test_short_title_rejected(self):
        form = TaskForm(self.data(title='ab'), project=self.project)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)


class TaskPermissionTests(TaskTestBase):
    def test_assignee_can_update_status(self):
        self.login('member')
        self.client.post(reverse('task_detail', args=[self.t_high.pk]), {'status': 'completed'})
        self.t_high.refresh_from_db()
        self.assertEqual(self.t_high.status, 'completed')

    def test_non_assignee_member_cannot_change_status(self):
        self.login('other')
        self.client.post(reverse('task_detail', args=[self.t_high.pk]), {'status': 'completed'})
        self.t_high.refresh_from_db()
        self.assertEqual(self.t_high.status, 'todo')

    def test_assignee_cannot_edit_or_delete_task(self):
        self.login('member')
        self.assertEqual(self.client.get(reverse('task_update', args=[self.t_high.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('task_delete', args=[self.t_high.pk])).status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.t_high.pk).exists())

    def test_member_cannot_create_task(self):
        self.login('member')
        self.assertEqual(self.client.get(reverse('task_create', args=[self.project.pk])).status_code, 403)

    def test_outsider_cannot_view_task(self):
        self.login('outsider')
        self.assertEqual(self.client.get(reverse('task_detail', args=[self.t_high.pk])).status_code, 403)

    def test_manager_can_create_task(self):
        self.login('manager')
        self.client.post(reverse('task_create', args=[self.project.pk]), {
            'title': 'Manager task', 'description': '', 'assigned_to': self.member.pk,
            'priority': 'low', 'status': 'todo', 'deadline': self.today + timedelta(days=2),
        })
        task = Task.objects.get(title='Manager task')
        self.assertEqual(task.created_by, self.manager)
        self.assertEqual(task.project, self.project)

    def test_manager_can_delete_task(self):
        self.login('manager')
        self.client.post(reverse('task_delete', args=[self.t_low.pk]))
        self.assertFalse(Task.objects.filter(pk=self.t_low.pk).exists())


class TaskListTests(TaskTestBase):
    def test_mine_shows_only_assigned_tasks(self):
        self.login('member')
        titles = self.titles(self.client.get(reverse('task_list')))
        self.assertCountEqual(titles, ['Write report', 'Fix bug'])

    def test_all_shows_project_tasks_but_never_other_teams(self):
        self.login('member')
        titles = self.titles(self.client.get(reverse('task_list'), {'scope': 'all'}))
        self.assertIn('Design logo', titles)
        self.assertNotIn('Secret task', titles)

    def test_search_is_case_insensitive(self):
        self.login('member')
        titles = self.titles(self.client.get(reverse('task_list'), {'scope': 'all', 'q': 'REPORT'}))
        self.assertEqual(titles, ['Write report'])

    def test_filter_by_priority(self):
        self.login('member')
        titles = self.titles(self.client.get(reverse('task_list'), {'priority': 'low'}))
        self.assertEqual(titles, ['Fix bug'])

    def test_sort_by_priority_high_first(self):
        self.login('member')
        titles = self.titles(self.client.get(reverse('task_list'), {'sort': '-priority_rank'}))
        self.assertEqual(titles, ['Write report', 'Fix bug'])

    def test_overdue_filter(self):
        Task.objects.create(project=self.project, title='Old task', assigned_to=self.member,
                            deadline=self.today - timedelta(days=2), created_by=self.manager)
        self.login('member')
        titles = self.titles(self.client.get(reverse('task_list'), {'overdue': 'yes'}))
        self.assertEqual(titles, ['Old task'])

    def test_invalid_filter_value_does_not_crash(self):
        self.login('member')
        response = self.client.get(reverse('task_list'), {'status': 'hack', 'sort': 'password'})
        self.assertEqual(response.status_code, 200)