from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from projects.models import Project
from tasks.models import Task


@login_required
def dashboard(request):
    user = request.user

    # Admins see everything; others see only projects they belong to.
    if user.is_superuser:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(memberships__user=user).distinct()
    tasks = Task.objects.filter(project__in=projects)

    today = timezone.localdate()
    total_tasks = tasks.count()
    completed = tasks.filter(status=Task.Status.COMPLETED).count()
    pending = total_tasks - completed
    overdue_qs = tasks.exclude(status=Task.Status.COMPLETED).filter(deadline__lt=today)

    context = {
        'total_projects': projects.count(),
        'total_tasks': total_tasks,
        'completed': completed,
        'pending': pending,
        'overdue': overdue_qs.count(),
        'projects': projects[:6],
        'my_tasks': (
            Task.objects.filter(assigned_to=user)
            .exclude(status=Task.Status.COMPLETED)
            .select_related('project')
            .order_by('deadline')[:5]
        ),
        'overdue_tasks': overdue_qs.select_related('project', 'assigned_to').order_by('deadline')[:5],
        'today': today,
    }
    return render(request, 'dashboard/dashboard.html', context)