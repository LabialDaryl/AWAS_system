from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
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
def mark_notifications_viewed(request):
    """Mark notifications as viewed by storing a timestamp in the session.
    The badge count will be zeroed until newer notifications exist.
    """
    # Accept GET or POST for simplicity
    request.session['notifications_cleared_at'] = timezone.now().isoformat()
    request.session.modified = True
    return JsonResponse({'ok': True})


@login_required
def mark_notification_read(request):
    """Mark a single notification as read by ID (session-based)."""
    notif_id = request.GET.get('id')
    if not notif_id:
        return JsonResponse({'ok': False, 'error': 'missing id'}, status=400)
    read_ids = set(request.session.get('notifications_read_ids', []))
    read_ids.add(notif_id)
    request.session['notifications_read_ids'] = list(read_ids)
    request.session.modified = True
    return JsonResponse({'ok': True})


@login_required
def mark_all_notifications_read(request):
    """Mark all current notifications as read for the logged-in customer."""
    user = request.user
    if not getattr(user, 'is_customer', False):
        # Staff have no badge; no-op
        request.session['notifications_read_ids'] = []
        request.session.modified = True
        return JsonResponse({'ok': True})

    # Build current notification IDs (mirror context processor logic)
    from datetime import timedelta
    from django.conf import settings
    from billing.models import Bill, WaterUpdate

    now = timezone.now().date()
    days_before_due = getattr(settings, 'NOTIFICATION_DAYS_BEFORE_DUE', 5)

    ids = []
    for bill in Bill.objects.filter(customer=user, payment_status='unpaid')[:5]:
        ids.append(f"bill:{bill.id}:unpaid")

    due_soon_qs = Bill.objects.filter(
        customer=user,
        payment_status__in=['unpaid', 'partially_paid'],
        due_date__gt=now,
        due_date__lte=now + timedelta(days=days_before_due)
    )
    for bill in due_soon_qs[:5]:
        ids.append(f"bill:{bill.id}:due")

    updates_qs = WaterUpdate.objects.filter(is_active=True).order_by('-posted_at')[:10]
    user_purok = getattr(user, 'purok_number', None)
    for upd in updates_qs:
        target_ok = True
        if upd.target_puroks:
            try:
                targets = [int(p.strip()) for p in upd.target_puroks.split(',') if p.strip().isdigit()]
            except Exception:
                targets = []
            target_ok = bool(user_purok and user_purok in targets)
        if target_ok:
            ids.append(f"update:{upd.id}")

    request.session['notifications_read_ids'] = list(set(ids))
    request.session.modified = True
    return JsonResponse({'ok': True})
