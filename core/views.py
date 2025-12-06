from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from notifications.models import Notification
from .forms import ConnectionRequestForm
from billing.models import WaterUpdate


def landing_page(request):
    """Public landing page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    return render(request, 'landing/index.html')


def connection_request(request):
    """Handle water connection membership requests"""
    if request.method == 'POST':
        form = ConnectionRequestForm(request.POST)
        if form.is_valid():
            membership_request = form.save()
            messages.success(
                request, 
                'Your water connection request has been submitted successfully! '
                'Our staff will review your request and contact you soon.'
            )
            return redirect('core:landing')
    else:
        form = ConnectionRequestForm()
    
    # If it's an AJAX request (modal submission), return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        if request.method == 'POST':
            if form.is_valid():
                return JsonResponse({'success': True, 'message': 'Request submitted successfully!'})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
    
    return render(request, 'landing/connection_request.html', {'form': form})


@login_required
def home(request):
    """Home page - redirects based on user type"""
    if request.user.is_staff or request.user.user_type == 'staff':
        return redirect('billing:staff_dashboard')
    else:
        return redirect('billing:customer_dashboard')


def about(request):
    """About page"""
    return render(request, 'landing/about.html')


def contact(request):
    """Contact page"""
    return render(request, 'landing/contact.html')


@login_required
@require_http_methods(["POST"])
def mark_notifications_viewed(request):
    """
    Backwards-compatible endpoint to mark all notifications as viewed.
    
    Kept for older frontend code that may still call /notifications/mark-viewed/.
    It simply delegates to mark_all_notifications_read so behavior stays consistent.
    """
    return mark_all_notifications_read(request)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request):
    """Mark a single notification as read in the database."""
    notification_id = request.GET.get('id')
    if not notification_id:
        return JsonResponse({'ok': False, 'error': 'Missing notification ID'}, status=400)

    try:
        # Get the notification and verify ownership
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user,
            unread=True
        )
        notification.mark_as_read()
        return JsonResponse({
            'ok': True,
            'remaining': Notification.objects.filter(recipient=request.user, unread=True).count()
        })
    except Notification.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all unread notifications as read for the current user."""
    try:
        # Mark all unread notifications as read
        updated = Notification.objects.filter(
            recipient=request.user,
            unread=True
        ).update(unread=False)
        
        return JsonResponse({
            'ok': True,
            'count': updated
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
