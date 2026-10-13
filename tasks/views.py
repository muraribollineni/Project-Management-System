from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from projects.models import Project
from projects.permissions import can_manage_project, is_project_member

from .forms import TaskForm, TaskStatusForm
from .models import Task


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