from django import forms
from django.contrib.auth.models import User

from .models import Task


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css


class TaskForm(BootstrapMixin, forms.ModelForm):
    """Used by managers: all fields. Only project members can be assigned."""

    class Meta:
        model = Task
        fields = ('title', 'description', 'assigned_to', 'priority', 'status', 'deadline')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'deadline': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields['assigned_to'].queryset = User.objects.filter(
            memberships__project=project
        ).order_by('username')
        self.instance.project = project  # lets Task.clean() run its membership check


class TaskStatusForm(BootstrapMixin, forms.ModelForm):
    """Used by team members: they may only change the status."""

    class Meta:
        model = Task
        fields = ('status',)