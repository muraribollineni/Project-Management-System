from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from projects.models import Project
from projects.permissions import can_manage_project, is_project_member

from .forms import TaskForm, TaskStatusForm
from .models import Task

from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from .forms import TaskFilterForm, TaskForm, TaskStatusForm


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task.objects.select_related('project', 'assigned_to'), pk=pk)
    if not is_project_member(request.user, task.project):
        raise PermissionDenied
    can_manage = can_manage_project(request.user, task.project)
    is_assignee = task.assigned_to_id == request.user.id

    status_form = None
    if can_manage or is_assignee:
        status_form = TaskStatusForm(request.POST or None, instance=task)
        if request.method == 'POST' and status_form.is_valid():
            status_form.save()
            messages.success(request, 'Status updated.')
            return redirect('task_detail', pk=task.pk)

    return render(request, 'tasks/task_detail.html', {
        'task': task,
        'can_manage': can_manage,
        'status_form': status_form,
    })


@login_required
def task_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if not can_manage_project(request.user, project):
        raise PermissionDenied
    form = TaskForm(request.POST or None, project=project)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.project = project
        task.created_by = request.user
        task.save()
        messages.success(request, 'Task created.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': f'New task in {project.name}', 'project': project,
    })


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_manage_project(request.user, task.project):
        raise PermissionDenied
    form = TaskForm(request.POST or None, instance=task, project=task.project)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Task updated.')
        return redirect('task_detail', pk=task.pk)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': 'Edit task', 'project': task.project,
    })


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_manage_project(request.user, task.project):
        raise PermissionDenied
    project_id = task.project_id
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('project_detail', pk=project_id)
    return render(request, 'tasks/task_confirm_delete.html', {'task': task})

@login_required
def task_list(request):
    user = request.user

    # Only tasks from projects the user belongs to (admins see all).
    if user.is_superuser:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(memberships__user=user).distinct()

    # 'scope=mine' shows only tasks assigned to the user.
    scope = request.GET.get('scope', 'mine')
    tasks = Task.objects.filter(project__in=projects).select_related('project', 'assigned_to')
    if scope == 'mine':
        tasks = tasks.filter(assigned_to=user)

    # Turn text priority into a number so sorting is Low < Medium < High.
    tasks = tasks.annotate(
        priority_rank=Case(
            When(priority=Task.Priority.LOW, then=Value(1)),
            When(priority=Task.Priority.MEDIUM, then=Value(2)),
            When(priority=Task.Priority.HIGH, then=Value(3)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )

    form = TaskFilterForm(request.GET or None, projects=projects)
    sort = 'deadline'
    if form.is_valid():
        data = form.cleaned_data
        if data['q']:
            tasks = tasks.filter(Q(title__icontains=data['q']) | Q(description__icontains=data['q']))
        if data['status']:
            tasks = tasks.filter(status=data['status'])
        if data['priority']:
            tasks = tasks.filter(priority=data['priority'])
        if data['project']:
            tasks = tasks.filter(project=data['project'])
        if data['overdue'] == 'yes':
            tasks = tasks.exclude(status=Task.Status.COMPLETED).filter(deadline__lt=timezone.localdate())
        sort = data['sort'] or 'deadline'

    tasks = tasks.order_by(sort, 'id')

    paginator = Paginator(tasks, 10)
    page = paginator.get_page(request.GET.get('page'))

    # Keep the filters in the page links (everything except 'page').
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'tasks/task_list.html', {
        'form': form,
        'page': page,
        'scope': scope,
        'querystring': params.urlencode(),
        'today': timezone.localdate(),
    })