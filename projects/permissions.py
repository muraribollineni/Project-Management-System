from .models import ProjectMembership


def is_manager_role(user):
    """Admins and users whose profile role is Manager may create projects."""
    return user.is_superuser or (
        hasattr(user, 'profile') and user.profile.role == 'manager'
    )


def can_manage_project(user, project):
    """Admin, or a manager of this specific project."""
    if user.is_superuser:
        return True
    return ProjectMembership.objects.filter(
        project=project, user=user, role=ProjectMembership.Role.MANAGER
    ).exists()


def is_project_member(user, project):
    if user.is_superuser:
        return True
    return project.memberships.filter(user=user).exists()