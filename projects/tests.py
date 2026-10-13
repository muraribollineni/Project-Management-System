from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task

from .models import Project, ProjectMembership

PASSWORD = 'Str0ngPass!234'


class ProjectTestBase(TestCase):
    """Creates four users and one project that every test can use."""

    @classmethod
    def setUpTestData(cls):
        today = timezone.localdate()
        cls.today = today
        cls.admin = User.objects.create_superuser('admin', 'a@example.com', PASSWORD)
        cls.manager = User.objects.create_user('manager', 'm@example.com', PASSWORD)
        cls.manager.profile.role = 'manager'
        cls.manager.profile.save()
        cls.member = User.objects.create_user('member', 'mem@example.com', PASSWORD)
        cls.outsider = User.objects.create_user('outsider', 'o@example.com', PASSWORD)

        cls.project = Project.objects.create(
            name='Alpha',
            start_date=today - timedelta(days=10),
            deadline=today + timedelta(days=30),
            created_by=cls.manager,
        )
        ProjectMembership.objects.create(project=cls.project, user=cls.manager, role='manager')
        ProjectMembership.objects.create(project=cls.project, user=cls.member, role='member')

    def login(self, username):
        self.assertTrue(self.client.login(username=username, password=PASSWORD))


class ProjectModelTests(ProjectTestBase):
    def test_deadline_before_start_is_invalid(self):
        project = Project(name='Bad', start_date=self.today, deadline=self.today - timedelta(days=1))
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_same_user_cannot_join_project_twice(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProjectMembership.objects.create(project=self.project, user=self.member)

    def test_progress_is_percentage_of_completed_tasks(self):
        self.assertEqual(self.project.progress, 0)  # no tasks yet
        for status in ('completed', 'todo'):
            Task.objects.create(project=self.project, title=f'T-{status}', status=status,
                                deadline=self.today, created_by=self.manager)
        self.assertEqual(self.project.progress, 50)

    def test_deleting_project_deletes_its_tasks_and_memberships(self):
        Task.objects.create(project=self.project, title='Temp', deadline=self.today,
                            created_by=self.manager)
        self.project.delete()
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(ProjectMembership.objects.count(), 0)


class ProjectPermissionTests(ProjectTestBase):
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse('project_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_member_can_view_project(self):
        self.login('member')
        self.assertEqual(self.client.get(reverse('project_detail', args=[self.project.pk])).status_code, 200)

    def test_outsider_cannot_view_project(self):
        self.login('outsider')
        self.assertEqual(self.client.get(reverse('project_detail', args=[self.project.pk])).status_code, 403)

    def test_project_list_shows_only_own_projects(self):
        self.login('outsider')
        response = self.client.get(reverse('project_list'))
        self.assertNotContains(response, 'Alpha')

    def test_member_cannot_create_project(self):
        self.login('member')
        self.assertEqual(self.client.get(reverse('project_create')).status_code, 403)

    def test_manager_can_create_project_and_becomes_its_manager(self):
        self.login('manager')
        response = self.client.post(reverse('project_create'), {
            'name': 'Beta', 'description': 'x', 'status': 'planned',
            'start_date': self.today, 'deadline': self.today + timedelta(days=5),
        })
        project = Project.objects.get(name='Beta')
        self.assertRedirects(response, reverse('project_detail', args=[project.pk]))
        self.assertTrue(
            ProjectMembership.objects.filter(project=project, user=self.manager, role='manager').exists()
        )

    def test_invalid_dates_rejected_by_server(self):
        self.login('manager')
        response = self.client.post(reverse('project_create'), {
            'name': 'Bad', 'description': '', 'status': 'planned',
            'start_date': self.today, 'deadline': self.today - timedelta(days=3),
        })
        self.assertContains(response, 'Deadline cannot be before')
        self.assertFalse(Project.objects.filter(name='Bad').exists())

    def test_member_cannot_edit_project(self):
        self.login('member')
        url = reverse('project_update', args=[self.project.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.post(url, {'name': 'Hacked', 'status': 'completed',
                               'start_date': self.today, 'deadline': self.today})
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Alpha')

    def test_manager_can_edit_project(self):
        self.login('manager')
        self.client.post(reverse('project_update', args=[self.project.pk]), {
            'name': 'Alpha v2', 'description': '', 'status': 'in_progress',
            'start_date': self.project.start_date, 'deadline': self.project.deadline,
        })
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Alpha v2')
        self.assertEqual(self.project.status, 'in_progress')

    def test_member_cannot_delete_project(self):
        self.login('member')
        response = self.client.post(reverse('project_delete', args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_get_request_does_not_delete_project(self):
        self.login('manager')
        self.client.get(reverse('project_delete', args=[self.project.pk]))
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_manager_can_delete_project_with_post(self):
        self.login('manager')
        self.client.post(reverse('project_delete', args=[self.project.pk]))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_admin_can_edit_any_project(self):
        self.login('admin')
        self.assertEqual(self.client.get(reverse('project_update', args=[self.project.pk])).status_code, 200)

    def test_member_cannot_add_members(self):
        self.login('member')
        response = self.client.post(reverse('member_add', args=[self.project.pk]),
                                    {'user': self.outsider.pk, 'role': 'member'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.project.memberships.filter(user=self.outsider).exists())

    def test_manager_can_add_and_remove_member(self):
        self.login('manager')
        self.client.post(reverse('member_add', args=[self.project.pk]),
                         {'user': self.outsider.pk, 'role': 'member'})
        membership = self.project.memberships.get(user=self.outsider)
        self.client.post(reverse('member_remove', args=[self.project.pk, membership.pk]))
        self.assertFalse(self.project.memberships.filter(user=self.outsider).exists())