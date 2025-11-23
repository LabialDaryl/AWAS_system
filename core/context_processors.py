from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from billing.models import Bill, WaterUpdate
from django.urls import reverse
from django.utils.dateparse import parse_datetime


def notifications(request):
    """Provide notification count and a small list of items for the navbar.

    Customer notifications:
    - New/unpaid bills
    - Bills due within NOTIFICATION_DAYS_BEFORE_DUE days
    - Active water updates (targeted to user's purok or global)

    Staff notifications:
    - Active water updates (site-wide)
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user
    now = timezone.now().date()
    days_before_due = getattr(settings, 'NOTIFICATION_DAYS_BEFORE_DUE', 5)

    items = []

    if getattr(user, 'is_customer', False):
        # Unpaid bills
        unpaid_qs = Bill.objects.filter(customer=user, payment_status='unpaid')
        for bill in unpaid_qs[:5]:
            items.append({
                'type': 'bill',
                'icon': 'fas fa-file-invoice-dollar',
                'text': f"Unpaid bill for {bill.billing_month.strftime('%b %Y')}",
                'url': reverse('billing:customer_bills'),
                'id': f"bill:{bill.id}:unpaid",
            })

        # Due soon bills (strictly in next N days)
        due_soon_qs = Bill.objects.filter(
            customer=user,
            payment_status__in=['unpaid', 'partially_paid'],
            due_date__gt=now,
            due_date__lte=now + timedelta(days=days_before_due)
        )
        for bill in due_soon_qs[:5]:
            days_left = (bill.due_date - now).days
            items.append({
                'type': 'due_soon',
                'icon': 'fas fa-hourglass-half',
                'text': f"Bill due in {days_left} day(s) - {bill.billing_month.strftime('%b %Y')}",
                'url': reverse('billing:customer_bills'),
                'id': f"bill:{bill.id}:due",
            })

        # Water updates targeted to user's purok or global
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
                    'type': 'update',
                    'icon': 'fas fa-bullhorn',
                    'text': upd.title or f"{upd.update_type} update",
                    'url': reverse('billing:public_water_updates'),
                    'id': f"update:{upd.id}",
                })

    else:
        # Staff/admin: show active water updates and pending membership requests
        updates_qs = WaterUpdate.objects.filter(is_active=True).order_by('-posted_at')[:10]
        for upd in updates_qs:
            items.append({
                'type': 'update',
                'icon': 'fas fa-bullhorn',
                'text': (upd.title or upd.update_type) + ' (active)',
                'url': reverse('billing:public_water_updates'),
                'id': f"update:{upd.id}",
            })
            
        # Add pending membership requests for staff
        if hasattr(request.user, 'is_staff_member') and request.user.is_staff_member:
            from accounts.models import MembershipRequest
            pending_count = MembershipRequest.objects.filter(status='pending').count()
            if pending_count > 0:
                items.insert(0, {
                    'type': 'membership',
                    'icon': 'fas fa-user-plus',
                    'text': f"{pending_count} pending membership request{'s' if pending_count > 1 else ''} to review",
                    'url': reverse('billing:membership_requests'),
                    'id': 'membership:requests',
                    'priority': 1,  # Higher priority to show at the top
                })

    # Only customers should see a notification count badge
    if getattr(user, 'is_customer', False):
        # Per-item read tracking via session
        read_ids = set(request.session.get('notifications_read_ids', []))
        count = sum(1 for i in items if i.get('id') and i['id'] not in read_ids)
    else:
        count = 0

    # Limit items shown in dropdown for performance
    return {
        'notification_count': count,
        'notification_items': items[:8],
    }
