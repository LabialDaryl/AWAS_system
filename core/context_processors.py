from datetime import timedelta, datetime
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from notifications.models import Notification
from billing.models import Bill, WaterUpdate
from accounts.models import MembershipRequest


def notifications(request):
    """Provide notification count and a small list of items for the navbar.
    
    Uses the django-notifications-hq package to store and manage notifications.
    """
    if not request.user.is_authenticated:
        return {
            'notification_count': 0,
            'notification_items': []
        }

    # Get unread notifications for the current user from the database
    unread_qs = Notification.objects.filter(
        recipient=request.user,
        unread=True
    ).select_related('actor_content_type', 'target_content_type').order_by('-timestamp')[:10]

    notification_items = []
    for n in unread_qs:
        # Determine the appropriate icon based on the verb
        icon_map = {
            'commented': 'fa-comment',
            'mentioned': 'fa-at',
            'followed': 'fa-user-plus',
            'liked': 'fa-heart',
            'shared': 'fa-retweet',
            'bill': 'fa-file-invoice-dollar',
            'due_soon': 'fa-hourglass-half',
            'update': 'fa-bullhorn',
            'membership': 'fa-user-plus',
        }
        
        # Default icon if verb not in map
        icon = f"fas {icon_map.get(n.verb, 'fa-bell')}"
        
        # Get the target URL if available
        url = '#'
        try:
            # Try to get the target object if it exists
            target = n.target
            if hasattr(target, 'get_absolute_url'):
                url = target.get_absolute_url()
        except:
            pass
        
        # Create a human-readable description if none exists
        description = n.description or n.verb
        if not description and hasattr(n, 'data') and isinstance(n.data, dict):
            description = n.data.get('message', 'New notification')
        
        notification_items.append({
            'id': str(n.id),
            'text': description or 'New notification',
            'url': url,
            'icon': icon,
            'unread': n.unread,
            'timestamp': n.timestamp,
            'type': n.verb.split('.')[-1] if n.verb else 'notification',
        })

    # Add system notifications (bills, water updates, etc.).
    # These are informational and should not affect the unread badge count.
    system_notifications = get_system_notifications(request)
    notification_items.extend(system_notifications)
    
    # Sort by timestamp (newest first)
    notification_items.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
    
    # Badge count reflects only persistent unread notifications from the database
    unread_count = unread_qs.count()

    return {
        'notification_count': unread_count,
        'notification_items': notification_items[:8],  # Limit to 8 items for the dropdown
    }


def get_system_notifications(request):
    """Generate system notifications (bills, updates, etc.)"""
    if not request.user.is_authenticated:
        return []
        
    user = request.user
    now = timezone.now().date()
    days_before_due = getattr(settings, 'NOTIFICATION_DAYS_BEFORE_DUE', 5)
    items = []

    # Only generate system notifications for customers
    if getattr(user, 'is_customer', False):
        # Unpaid bills
        unpaid_qs = Bill.objects.filter(customer=user, payment_status='unpaid')
        for bill in unpaid_qs[:5]:
            items.append({
                'id': f"bill:{bill.id}:unpaid",
                'type': 'bill',
                'icon': 'fas fa-file-invoice-dollar',
                'text': f"Unpaid bill for {bill.billing_month.strftime('%b %Y')}",
                'url': reverse('billing:customer_bills'),
                'unread': False,
                'timestamp': bill.created_at,
            })

        # Due soon bills
        due_soon_qs = Bill.objects.filter(
            customer=user,
            payment_status__in=['unpaid', 'partially_paid'],
            due_date__gt=now,
            due_date__lte=now + timedelta(days=days_before_due)
        )
        for bill in due_soon_qs[:5]:
            days_left = (bill.due_date - now).days
            items.append({
                'id': f"bill:{bill.id}:due",
                'type': 'due_soon',
                'icon': 'fas fa-hourglass-half',
                'text': f"Bill due in {days_left} day(s) - {bill.billing_month.strftime('%b %Y')}",
                'url': reverse('billing:customer_bills'),
                'unread': False,
                'timestamp': bill.due_date,
            })

        # Water updates
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
                items.append({
                    'id': f"update:{upd.id}",
                    'type': 'update',
                    'icon': 'fas fa-bullhorn',
                    'text': upd.title or f"{upd.update_type} update",
                    'url': reverse('billing:public_water_updates'),
                    'unread': False,
                    'timestamp': upd.posted_at or timezone.now(),
                })
    
    # Staff notifications
    if hasattr(user, 'is_staff_member') and user.is_staff_member:
        # Pending membership requests
        pending_count = MembershipRequest.objects.filter(status='pending').count()
        if pending_count > 0:
            items.append({
                'id': 'membership:requests',
                'type': 'membership',
                'icon': 'fas fa-user-plus',
                'text': f"{pending_count} pending membership request{'s' if pending_count > 1 else ''} to review",
                'url': reverse('billing:membership_requests'),
                'unread': False,
                'timestamp': timezone.now(),
                'priority': 1,
            })
    
    return items
