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

    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        project = self.project
        if project and deadline > project.deadline:
            raise forms.ValidationError(
                f'Task deadline cannot be after the project deadline ({project.deadline}).'
            )
        return deadline

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 3:
            raise forms.ValidationError('Title must be at least 3 characters.')
        return title

class TaskStatusForm(BootstrapMixin, forms.ModelForm):
    """Used by team members: they may only change the status."""

    class Meta:
        model = Task
        fields = ('status',)
class TaskFilterForm(forms.Form):
    SORT_CHOICES = [
        ('deadline', 'Deadline (earliest first)'),
        ('-deadline', 'Deadline (latest first)'),
        ('-priority_rank', 'Priority (high to low)'),
        ('priority_rank', 'Priority (low to high)'),
        ('-created_at', 'Newest first'),
    ]
    OVERDUE_CHOICES = [('', 'All'), ('yes', 'Overdue only')]

    q = forms.CharField(required=False, label='Search',
                        widget=forms.TextInput(attrs={'placeholder': 'Search title or description'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All statuses')] + list(Task.Status.choices))
    priority = forms.ChoiceField(required=False, choices=[('', 'All priorities')] + list(Task.Priority.choices))
    project = forms.ModelChoiceField(required=False, queryset=None, empty_label='All projects')
    overdue = forms.ChoiceField(required=False, choices=OVERDUE_CHOICES)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = projects
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css