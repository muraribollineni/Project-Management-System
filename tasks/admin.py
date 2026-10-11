from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'priority', 'status', 'deadline')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title',)