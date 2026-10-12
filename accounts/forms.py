from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    role = forms.ChoiceField(choices=Profile.Role.choices, initial=Profile.Role.MEMBER)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # The signal already created the Profile; we only set the chosen role.
            user.profile.role = self.cleaned_data['role']
            user.profile.save()
        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This email is used by another account.')
        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone', 'bio')
        widgets = {'bio': forms.Textarea(attrs={'rows': 3})}


def _style_fields(form):
    for field in form.fields.values():
        css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        field.widget.attrs['class'] = css


for _form in (RegisterForm, UserUpdateForm, ProfileUpdateForm):
    _original_init = _form.__init__

    def _new_init(self, *args, _orig=_original_init, **kwargs):
        _orig(self, *args, **kwargs)
        _style_fields(self)

    _form.__init__ = _new_init