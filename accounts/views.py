from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileUpdateForm, RegisterForm, UserUpdateForm
from .models import Profile

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect('profile')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=user_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=user_profile)
    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })