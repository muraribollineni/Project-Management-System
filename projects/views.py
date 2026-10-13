from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AddMemberForm, ProjectForm
from .models import Project, ProjectMembership
from .permissions import can_manage_project, is_manager_role, is_project_member


@login_required
def project_list(request):
    if request.user.is_superuser:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(memberships__user=request.user).distinct()
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not is_project_member(request.user, project):
        raise PermissionDenied
    return render(request, 'projects/project_detail.html', {
        'project': project,
        'memberships': project.memberships.select_related('user'),
        'tasks': project.tasks.select_related('assigned_to'),
        'can_manage': can_manage_project(request.user, project),
    })


@login_required
def project_create(request):
    if not is_manager_role(request.user):
        raise PermissionDenied
    form = ProjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        project = form.save(commit=False)
        project.created_by = request.user
        project.save()
        # The creator automatically becomes the project's manager.
        ProjectMembership.objects.create(
            project=project, user=request.user, role=ProjectMembership.Role.MANAGER
        )
        messages.success(request, 'Project created.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'New project'})


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise PermissionDenied
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Project updated.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Edit project'})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise PermissionDenied
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted.')
        return redirect('project_list')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@login_required
def member_add(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise PermissionDenied
    form = AddMemberForm(request.POST or None, project=project)
    if request.method == 'POST' and form.is_valid():
        ProjectMembership.objects.create(
            project=project,
            user=form.cleaned_data['user'],
            role=form.cleaned_data['role'],
        )
        messages.success(request, 'Member added.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/member_form.html', {'form': form, 'project': project})


@login_required
@require_POST
def member_remove(request, pk, membership_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise PermissionDenied
    membership = get_object_or_404(ProjectMembership, pk=membership_id, project=project)
    membership.delete()
    messages.success(request, 'Member removed.')
    return redirect('project_detail', pk=project.pk)