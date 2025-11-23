from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.core.paginator import Paginator
import csv
from urllib.parse import urlencode
from accounts.models import User, MembershipRequest
from complaints.models import Complaint
from payments.models import Payment
from .models import Bill, WaterUpdate
from .forms import BillCreateForm, BillUpdateForm, BillFilterForm, WaterUpdateForm


@login_required
def customer_dashboard(request):
    """Customer dashboard view"""
    if request.user.is_staff_member:
        return redirect('billing:staff_dashboard')
    
    # Get customer's bills
    recent_bills = list(
        Bill.objects.filter(customer=request.user).order_by('-billing_month')[:6]
    )
    # reverse to chronological order for charts
    recent_bills = list(reversed(recent_bills))
    unpaid_bills = Bill.objects.filter(customer=request.user, payment_status='unpaid')

    # Recent activities (combine bills created, payments made, complaints created/updated)
    recent_payments = Payment.objects.filter(customer=request.user).order_by('-payment_date')[:5]
    recent_customer_bills = Bill.objects.filter(customer=request.user).order_by('-created_at')[:5]
    recent_complaints = Complaint.objects.filter(customer=request.user).order_by('-updated_at')[:5]

    activities = []
    for p in recent_payments:
        activities.append({
            'when': p.payment_date,
            'type': 'payment',
            'title': f"Payment {p.reference_number} ({p.get_payment_status_display()})",
            'desc': f"₱{p.amount} for {p.bill.billing_month.strftime('%b %Y')} via {p.get_payment_method_display()}",
            'url': f"/payments/history/",
        })
    for b in recent_customer_bills:
        activities.append({
            'when': b.created_at,
            'type': 'bill',
            'title': f"Bill generated for {b.billing_month.strftime('%b %Y')}",
            'desc': f"Total ₱{b.total_amount} • Status: {b.get_payment_status_display()}",
            'url': f"/billing/customer/bill/{b.id}/",
        })
    for c in recent_complaints:
        activities.append({
            'when': c.updated_at,
            'type': 'complaint',
            'title': f"{c.get_type_display()} — {c.subject}",
            'desc': f"Status: {c.get_status_display()} • Priority: {c.get_priority_display()}",
            'url': f"/complaints/{c.id}/",
        })
    # Sort by time desc and take top 8
    activities.sort(key=lambda x: x['when'], reverse=True)
    recent_activities = activities[:3]
    
    # Get water updates for customer's purok
    water_updates = WaterUpdate.objects.filter(is_active=True)
    if request.user.purok_number:
        water_updates = water_updates.filter(
            Q(target_puroks='') | Q(target_puroks__contains=str(request.user.purok_number))
        )[:5]
    
    context = {
        'recent_bills': recent_bills,
        'unpaid_bills': unpaid_bills,
        'water_updates': water_updates,
        'total_unpaid': unpaid_bills.aggregate(Sum('balance'))['balance__sum'] or 0,
        # chart data
        'chart_labels': [b.billing_month.strftime('%b %Y') for b in recent_bills],
        'chart_consumption': [float(b.water_consumption) for b in recent_bills],
        'chart_prev': [float(b.previous_reading) for b in recent_bills],
        'chart_pres': [float(b.present_reading) for b in recent_bills],
        'recent_activities': recent_activities,
    }
    
    return render(request, 'customer/dashboard.html', context)


@login_required
def customer_bills(request):
    """List all customer bills"""
    bills = Bill.objects.filter(customer=request.user)
    return render(request, 'customer/bills.html', {'bills': bills})


@login_required
def bill_detail(request, bill_id):
    """View bill details"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check if user has permission to view this bill
    if bill.customer != request.user and not request.user.is_staff_member:
        messages.error(request, 'You do not have permission to view this bill.')
        return redirect('billing:customer_bills')
    
    return render(request, 'customer/bill_detail.html', {'bill': bill})


@login_required
def staff_dashboard(request):
    """Staff dashboard view"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('billing:customer_dashboard')
    
    # Statistics
    total_customers = User.objects.filter(user_type='customer', is_active=True).count()
    active_customers = User.objects.filter(
        user_type='customer', 
        is_active=True, 
        is_suspended=False
    ).count()
    suspended_customers = User.objects.filter(
        user_type='customer', 
        is_suspended=True
    ).count()
    
    # Bills statistics
    current_month = timezone.now().date().replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    unpaid_bills = Bill.objects.filter(payment_status='unpaid').count()
    overdue_bills = Bill.objects.filter(is_overdue=True).count()
    
    # Pending membership requests
    pending_requests = MembershipRequest.objects.filter(status='pending').count()
    
    # Recent bills
    recent_bills = Bill.objects.all().order_by('-created_at')[:10]

    # Recent payments (including walk-ins)
    recent_payments = Payment.objects.select_related('customer', 'bill').order_by('-payment_date')[:10]

    # Build unified recent activities
    activities = []
    for p in recent_payments:
        activities.append({
            'when': p.payment_date,
            'type': 'payment',
            'title': f"Payment {p.reference_number} ({p.get_payment_status_display()})",
            'desc': f"₱{p.amount} • {p.customer.get_full_name()} • {p.bill.billing_month.strftime('%b %Y')}",
            'url': "/payments/staff/payments/",
        })
    for b in recent_bills:
        activities.append({
            'when': b.created_at,
            'type': 'bill',
            'title': f"Bill generated for {b.customer.get_full_name()} — {b.billing_month.strftime('%b %Y')}",
            'desc': f"Total ₱{b.total_amount} • Status: {b.get_payment_status_display()}",
            'url': f"/billing/staff/bills/{b.id}/edit/",
        })
    # Recent complaints
    recent_complaints = Complaint.objects.select_related('customer').order_by('-updated_at')[:10]
    for c in recent_complaints:
        activities.append({
            'when': c.updated_at,
            'type': 'complaint',
            'title': f"{c.get_type_display()} — {c.subject}",
            'desc': f"{c.customer.get_full_name()} • Status: {c.get_status_display()} • Priority: {c.get_priority_display()}",
            'url': f"/billing/staff/complaints/",
        })
    # Recent membership requests processed
    recent_membership = MembershipRequest.objects.order_by('-processed_date', '-request_date')[:10]
    for mr in recent_membership:
        activities.append({
            'when': mr.processed_date or mr.request_date,
            'type': 'membership',
            'title': f"Membership {mr.get_status_display()} — {mr.first_name} {mr.last_name}",
            'desc': f"Requested: {mr.request_date.strftime('%Y-%m-%d')}" + (f" • By: {mr.processed_by.get_full_name()}" if mr.processed_by else ''),
            'url': f"/billing/staff/membership-requests/",
        })

    # Recent water updates (include in unified activities)
    for u in WaterUpdate.objects.order_by('-posted_at')[:10]:
        activities.append({
            'when': u.posted_at,
            'type': 'update',
            'title': f"{u.update_type}",
            'desc': f"Priority: {u.get_priority_display()}" + (f" • Puroks: {u.target_puroks}" if u.target_puroks else " • All Puroks"),
            'url': "/billing/staff/water-updates/",
        })

    activities.sort(key=lambda x: x['when'], reverse=True)
    recent_activities = activities[:3]

    # Recent water updates for quick view
    recent_water_updates = WaterUpdate.objects.order_by('-posted_at')[:5]
    
    # Per-purok stats (1..8)
    purok_stats = []
    for purok in range(1, 9):
        customers_qs = User.objects.filter(user_type='customer', purok_number=purok)
        total_cust = customers_qs.count()
        active_cust = customers_qs.filter(is_active=True, is_suspended=False).count()
        suspended_cust = customers_qs.filter(is_suspended=True).count()

        bills_qs = Bill.objects.filter(
            customer__in=customers_qs,
            billing_month__gte=current_month,
            billing_month__lt=next_month
        )
        paid_bills = bills_qs.filter(payment_status='paid').count()
        unpaid_bills_cnt = bills_qs.exclude(payment_status='paid').count()
        cust_with_bill = bills_qs.values('customer').distinct().count()
        cust_without_bill = max(total_cust - cust_with_bill, 0)
        revenue = bills_qs.aggregate(total_paid=Sum('amount_paid'))['total_paid'] or 0

        purok_stats.append({
            'purok': purok,
            'total_customers': total_cust,
            'active_customers': active_cust,
            'suspended_customers': suspended_cust,
            'paid_bills': paid_bills,
            'unpaid_bills': unpaid_bills_cnt,
            'with_bill': cust_with_bill,
            'without_bill': cust_without_bill,
            'revenue': revenue,
        })

    context = {
        'total_customers': total_customers,
        'active_customers': active_customers,
        'suspended_customers': suspended_customers,
        'unpaid_bills': unpaid_bills,
        'overdue_bills': overdue_bills,
        'pending_requests': pending_requests,
        'recent_bills': recent_bills,
        'recent_activities': recent_activities,
        'purok_stats': purok_stats,
        'recent_water_updates': recent_water_updates,
    }
    
    return render(request, 'staff/dashboard.html', context)


@login_required
def staff_activities(request):
    """Full activity feed for staff with pagination."""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    activities = []
    # Collect payments
    for p in Payment.objects.select_related('customer', 'bill').order_by('-payment_date')[:500]:
        activities.append({
            'when': p.payment_date,
            'type': 'payment',
            'title': f"Payment {p.reference_number} ({p.get_payment_status_display()})",
            'desc': f"₱{p.amount} • {p.customer.get_full_name()} • {p.bill.billing_month.strftime('%b %Y')}",
            'url': "/payments/staff/payments/",
        })
    # Collect bills
    for b in Bill.objects.select_related('customer').order_by('-created_at')[:500]:
        activities.append({
            'when': b.created_at,
            'type': 'bill',
            'title': f"Bill for {b.customer.get_full_name()} — {b.billing_month.strftime('%b %Y')}",
            'desc': f"Total ₱{b.total_amount} • Status: {b.get_payment_status_display()}",
            'url': f"/billing/staff/bills/{b.id}/edit/",
        })
    # Collect complaints
    for c in Complaint.objects.select_related('customer').order_by('-updated_at')[:500]:
        activities.append({
            'when': c.updated_at,
            'type': 'complaint',
            'title': f"{c.get_type_display()} — {c.subject}",
            'desc': f"{c.customer.get_full_name()} • Status: {c.get_status_display()} • Priority: {c.get_priority_display()}",
            'url': "/billing/staff/complaints/",
        })
    # Collect membership events
    for mr in MembershipRequest.objects.order_by('-processed_date', '-request_date')[:500]:
        activities.append({
            'when': mr.processed_date or mr.request_date,
            'type': 'membership',
            'title': f"Membership {mr.get_status_display()} — {mr.first_name} {mr.last_name}",
            'desc': f"Requested: {mr.request_date.strftime('%Y-%m-%d')}" + (f" • By: {mr.processed_by.get_full_name()}" if mr.processed_by else ''),
            'url': "/billing/staff/membership-requests/",
        })

    activities.sort(key=lambda x: x['when'], reverse=True)
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'staff/activities.html', {
        'page_obj': page_obj,
        'total_count': len(activities),
    })


@login_required
def create_bill(request):
    """Create a new bill"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Filters for easier selection
    purok = request.GET.get('purok')
    without_bill = request.GET.get('without_bill') == '1'
    
    if request.method == 'POST':
        # Keep the filtered queryset on POST as well
        form = BillCreateForm(request.POST, purok=purok, without_bill_this_month=without_bill)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.created_by = request.user
            bill.save()
            messages.success(request, f'Bill created successfully for {bill.customer.get_full_name()}.')
            return redirect('billing:staff_dashboard')
    else:
        form = BillCreateForm(purok=purok, without_bill_this_month=without_bill)
    
    return render(request, 'staff/create_bill.html', {
        'form': form,
        'purok_filter': (purok or ''),
        'without_bill': without_bill,
    })


@login_required
def edit_bill(request, bill_id):
    """Edit an existing bill"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    bill = get_object_or_404(Bill, id=bill_id)
    
    if request.method == 'POST':
        form = BillUpdateForm(request.POST, instance=bill)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bill updated successfully.')
            return redirect('billing:staff_dashboard')
    else:
        form = BillUpdateForm(instance=bill)
    
    return render(request, 'staff/edit_bill.html', {'form': form, 'bill': bill})


@login_required
def customer_list(request):
    """List all customers"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    customers = User.objects.filter(user_type='customer')
    
    # Filters
    status_filter = request.GET.get('status')
    purok_filter = request.GET.get('purok')
    bill_filter = request.GET.get('bill')  # 'this_month_with' | 'this_month_without'
    
    if status_filter == 'active':
        customers = customers.filter(is_active=True, is_suspended=False)
    elif status_filter == 'suspended':
        customers = customers.filter(is_suspended=True)
    
    if purok_filter:
        customers = customers.filter(purok_number=purok_filter)

    # Bill coverage filter for current month
    if bill_filter in ['this_month_with', 'this_month_without']:
        current_month = timezone.now().date().replace(day=1)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        if bill_filter == 'this_month_with':
            customers = customers.filter(
                bills__billing_month__gte=current_month,
                bills__billing_month__lt=next_month
            ).distinct()
        else:  # this_month_without
            customers = customers.exclude(
                bills__billing_month__gte=current_month,
                bills__billing_month__lt=next_month
            ).distinct()
    
    return render(request, 'staff/customer_list.html', {
        'customers': customers,
        'status_filter': status_filter or '',
        'purok_filter': purok_filter or '',
        'bill_filter': bill_filter or '',
    })


@login_required
def customer_detail(request, customer_id):
    """View customer details"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    customer = get_object_or_404(User, id=customer_id, user_type='customer')
    bills = Bill.objects.filter(customer=customer)
    
    context = {
        'customer': customer,
        'bills': bills,
        'total_unpaid': bills.filter(payment_status='unpaid').aggregate(Sum('balance'))['balance__sum'] or 0,
    }
    
    return render(request, 'staff/customer_detail.html', context)


@login_required
def suspend_customer(request, customer_id):
    """Suspend a customer"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    customer = get_object_or_404(User, id=customer_id, user_type='customer')
    customer.is_suspended = True
    customer.save()
    
    messages.success(request, f'{customer.get_full_name()} has been suspended.')
    return redirect('billing:customer_detail', customer_id=customer_id)


@login_required
def reinstate_customer(request, customer_id):
    """Reinstate a suspended customer"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    customer = get_object_or_404(User, id=customer_id, user_type='customer')
    customer.is_suspended = False
    customer.save()
    
    messages.success(request, f'{customer.get_full_name()} has been reinstated.')
    return redirect('billing:customer_detail', customer_id=customer_id)


@login_required
def membership_requests(request):
    """List membership requests"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    requests = MembershipRequest.objects.all()
    
    # Filter by status
    status_filter = request.GET.get('status', 'pending')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    return render(request, 'staff/membership_requests.html', {'requests': requests})


@login_required
def approve_membership(request, request_id):
    """Approve a membership request and create user account"""
    # Only admins can approve
    if not getattr(request.user, 'is_admin', False):
        messages.error(request, 'Only admins can approve membership requests.')
        return redirect('billing:membership_requests')
    
    membership_request = get_object_or_404(MembershipRequest, id=request_id)
    
    if membership_request.status != 'pending':
        messages.warning(request, 'This request has already been processed.')
        return redirect('billing:membership_requests')
    
    # Create user account
    username = f"{membership_request.first_name.lower()}{membership_request.last_name.lower()}"
    base_username = username
    counter = 1
    
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    user = User.objects.create_user(
        username=username,
        email=membership_request.email,
        first_name=membership_request.first_name,
        last_name=membership_request.last_name,
        password=User.objects.make_random_password(),
        user_type='customer',
        phone_number=membership_request.phone_number,
        purok_number=membership_request.purok_number,
        specific_address=membership_request.specific_address,
        connection_type=membership_request.connection_type,
        is_membership_approved=True,
        membership_request_date=membership_request.request_date
    )
    
    # Update membership request
    membership_request.status = 'approved'
    membership_request.processed_by = request.user
    membership_request.processed_date = timezone.now()
    membership_request.created_user = user
    membership_request.save()
    
    messages.success(
        request, 
        f'Membership approved! Account created with username: {username}. '
        f'Please inform the customer to reset their password.'
    )
    
    return redirect('billing:membership_requests')


@login_required
def reject_membership(request, request_id):
    """Reject a membership request"""
    # Only admins can reject
    if not getattr(request.user, 'is_admin', False):
        messages.error(request, 'Only admins can reject membership requests.')
        return redirect('billing:membership_requests')
    
    membership_request = get_object_or_404(MembershipRequest, id=request_id)
    
    if membership_request.status != 'pending':
        messages.warning(request, 'This request has already been processed.')
        return redirect('billing:membership_requests')
    
    membership_request.status = 'rejected'
    membership_request.processed_by = request.user
    membership_request.processed_date = timezone.now()
    membership_request.save()
    
    messages.success(request, 'Membership request has been rejected.')
    return redirect('billing:membership_requests')


@login_required
def water_updates_list(request):
    """List water updates for staff"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    updates = WaterUpdate.objects.all()
    return render(request, 'staff/water_updates.html', {'updates': updates})


@login_required
def create_water_update(request):
    """Create a new water update"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    if request.method == 'POST':
        form = WaterUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.posted_by = request.user
            update.save()
            messages.success(request, 'Water update posted successfully.')
            return redirect('billing:water_updates_list')
    else:
        form = WaterUpdateForm()
    
    return render(request, 'staff/create_water_update.html', {'form': form})


@login_required
def edit_water_update(request, update_id):
    """Edit a water update"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    update = get_object_or_404(WaterUpdate, id=update_id)
    
    if request.method == 'POST':
        form = WaterUpdateForm(request.POST, instance=update)
        if form.is_valid():
            form.save()
            messages.success(request, 'Water update updated successfully.')
            return redirect('billing:water_updates_list')
    else:
        form = WaterUpdateForm(instance=update)
    
    return render(request, 'staff/edit_water_update.html', {'form': form, 'update': update})


@login_required
def delete_water_update(request, update_id):
    """Delete a water update"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    update = get_object_or_404(WaterUpdate, id=update_id)
    update.delete()
    
    messages.success(request, 'Water update deleted successfully.')
    return redirect('billing:water_updates_list')


def public_water_updates(request):
    """Public view of water updates"""
    updates = WaterUpdate.objects.filter(is_active=True)
    
    if request.user.is_authenticated and request.user.purok_number:
        updates = updates.filter(
            Q(target_puroks='') | Q(target_puroks__contains=str(request.user.purok_number))
        )
    
    return render(request, 'billing/water_updates_public.html', {'updates': updates})


@login_required
def staff_complaints(request):
    """Staff complaints list with filters"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    qs = Complaint.objects.select_related('customer')

    # Filters
    status = request.GET.get('status')  # open, in_progress, resolved, closed
    type_ = request.GET.get('type')     # complaint, suggestion, inquiry, feedback
    purok = request.GET.get('purok')

    if status:
        qs = qs.filter(status=status)
    if type_:
        qs = qs.filter(type=type_)
    if purok:
        qs = qs.filter(customer__purok_number=purok)

    complaints = qs
    
    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="complaints.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Customer', 'Purok', 'Type', 'Priority', 'Status', 'Subject'])
        for c in complaints:
            writer.writerow([
                c.created_at.strftime('%Y-%m-%d'),
                c.customer.get_full_name(),
                c.customer.purok_number or '',
                c.get_type_display(),
                c.get_priority_display(),
                c.get_status_display(),
                c.subject,
            ])
        return response

    # Build export URL preserving current filters
    qd = request.GET.copy()
    qd['export'] = 'csv'
    export_url = f"/billing/staff/complaints/?{urlencode(qd, doseq=True)}"

    context = {
        'complaints': complaints,
        'status_filter': status or '',
        'type_filter': type_ or '',
        'purok_filter': purok or '',
        'export_url': export_url,
    }
    return render(request, 'staff/complaints.html', context)


@login_required
def staff_reports(request):
    """Staff reports: month filter and per-purok breakdown"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    # Month filter (YYYY-MM via input type=month). Default: current month
    month_str = request.GET.get('month')
    if month_str:
        try:
            current_month = datetime.strptime(month_str + '-01', '%Y-%m-%d').date()
        except ValueError:
            current_month = timezone.now().date().replace(day=1)
    else:
        current_month = timezone.now().date().replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)

    purok_param = request.GET.get('purok')

    bills_base = Bill.objects.filter(billing_month__gte=current_month, billing_month__lt=next_month)
    if purok_param:
        bills_base = bills_base.filter(customer__purok_number=purok_param)

    total_billed = bills_base.aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = bills_base.aggregate(total=Sum('amount_paid'))['total'] or 0
    paid_count = bills_base.filter(payment_status='paid').count()
    unpaid_count = bills_base.exclude(payment_status='paid').count()

    # Per-purok breakdown (1..8)
    purok_stats = []
    purok_range = range(1, 9) if not purok_param else [int(purok_param)]
    for purok in purok_range:
        bills_qs = Bill.objects.filter(
            customer__purok_number=purok,
            billing_month__gte=current_month,
            billing_month__lt=next_month
        )
        if purok_param and str(purok) != str(purok_param):
            continue
        total_billed_p = bills_qs.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid_p = bills_qs.aggregate(total=Sum('amount_paid'))['total'] or 0
        paid_bills = bills_qs.filter(payment_status='paid').count()
        unpaid_bills = bills_qs.exclude(payment_status='paid').count()
        customers_total = User.objects.filter(user_type='customer', purok_number=purok).count()
        customers_with_bill = bills_qs.values('customer').distinct().count()
        customers_without_bill = max(customers_total - customers_with_bill, 0)

        purok_stats.append({
            'purok': purok,
            'total_billed': total_billed_p,
            'total_paid': total_paid_p,
            'paid_bills': paid_bills,
            'unpaid_bills': unpaid_bills,
            'with_bill': customers_with_bill,
            'without_bill': customers_without_bill,
        })

    # CSV export of per-purok breakdown
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            "attachment; filename=\"reports_" + current_month.strftime('%Y_%m') + ".csv\""
        )
        writer = csv.writer(response)
        writer.writerow(['Month', current_month.strftime('%Y-%m')])
        writer.writerow(['Total Billed', total_billed])
        writer.writerow(['Total Paid', total_paid])
        writer.writerow(['Paid Bills', paid_count])
        writer.writerow(['Unpaid Bills', unpaid_count])
        writer.writerow([])
        writer.writerow(['Purok', 'Total Billed', 'Total Paid', 'Paid Bills', 'Unpaid Bills', 'With Bill', 'Without Bill'])
        for s in purok_stats:
            writer.writerow([
                s['purok'], s['total_billed'], s['total_paid'], s['paid_bills'], s['unpaid_bills'], s['with_bill'], s['without_bill']
            ])
        return response

    # Build export URL preserving current filters
    qd = request.GET.copy()
    qd['export'] = 'csv'
    export_url = f"/billing/staff/reports/?{urlencode(qd, doseq=True)}"

    context = {
        'report_month': current_month,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'purok_stats': purok_stats,
        'purok_filter': purok_param or '',
        'month_filter': month_str or current_month.strftime('%Y-%m'),
        'export_url': export_url,
    }
    return render(request, 'staff/reports.html', context)
