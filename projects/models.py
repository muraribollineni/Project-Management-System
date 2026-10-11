from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    deadline = models.DateField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANNED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMembership',
        related_name='projects',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValidationError({'deadline': 'Deadline cannot be before the start date.'})

    @property
    def progress(self):
        """Percentage of tasks completed (0 if there are no tasks)."""
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter(status='completed').count()
        return round(done * 100 / total)


class ProjectMembership(models.Model):
    """Bridge table: which user belongs to which project, and in what role."""

    class Role(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        MEMBER = 'member', 'Member'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_project_user'),
        ]

    def __str__(self):
        return f'{self.user.username} in {self.project.name} ({self.role})'