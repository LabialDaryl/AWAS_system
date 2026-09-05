from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User
from .forms import UserLoginForm, UserProfileForm, UserSearchForm, CustomerSelfRegistrationForm


def user_login(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_suspended:
                    messages.error(request, 'Your account has been suspended. Please contact staff.')
                    return redirect('core:landing')
                
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)

                # Redirect based on user type
                if user.is_staff or user.user_type == 'staff':
                    return redirect('billing:staff_dashboard')
                else:
                    return redirect('billing:customer_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    # If it's an AJAX request (modal submission), return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        if request.method == 'POST':
            if form.is_valid():
                next_url = request.GET.get('next', '')
                if not next_url or not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
                    next_url = '/'
                return JsonResponse({'success': True, 'redirect': next_url})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
    
    return render(request, 'accounts/login.html', {'form': form})


def staff_login(request):
    """Dedicated staff login page; blocks non-staff users"""
    if request.user.is_authenticated:
        # If already logged in but not staff, send to customer dashboard
        if not request.user.is_staff_member:
            messages.error(request, 'This page is for staff only.')
            return redirect('billing:customer_dashboard')
        return redirect('billing:staff_dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and (user.is_staff or getattr(user, 'user_type', '') == 'staff'):
                if user.is_suspended:
                    messages.error(request, 'Your account has been suspended. Please contact admin.')
                    return redirect('accounts:staff_login')
                login(request, user)
                messages.success(request, f'Welcome, {user.get_full_name()}!')
                return redirect('billing:staff_dashboard')
            else:
                messages.error(request, 'Staff access only. Please use the customer login.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    return render(request, 'accounts/staff_login.html', {'form': form})


@login_required
def user_logout(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:landing')


def register_info(request):
    """Public self-registration: collects basic required info and creates account"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomerSelfRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto login newly registered user
            raw_password = form.cleaned_data.get('password1')
            auth_user = authenticate(username=user.username, password=raw_password)
            if auth_user is not None:
                login(request, auth_user)
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('billing:customer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerSelfRegistrationForm()
    
    # If it's an AJAX request (modal submission), return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        if request.method == 'POST':
            if form.is_valid():
                return JsonResponse({'success': True, 'redirect': '/customer/dashboard/'})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def user_profile(request):
    """Display user profile"""
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def search_users(request):
    """Search for registered users"""
    form = UserSearchForm(request.GET or None)
    users = User.objects.filter(is_active=True, user_type='customer')
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        purok_filter = form.cleaned_data.get('purok_filter')
        
        if search_query:
            users = users.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )
        
        if purok_filter:
            users = users.filter(purok_number=purok_filter)
    
    return render(request, 'accounts/user_search.html', {
        'form': form,
        'users': users
    })
