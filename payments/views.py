from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from billing.models import Bill
from .models import Payment, PaymentHistory
from .forms import OnlinePaymentForm, WalkInPaymentForm, PaymentVerificationForm
from django.conf import settings
from django.core.mail import send_mail
from accounts.models import User
from django.db import models


@login_required
def initiate_payment(request, bill_id):
    """Initiate payment for a bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check if user owns this bill
    if bill.customer != request.user:
        messages.error(request, 'You do not have permission to pay this bill.')
        return redirect('billing:customer_bills')
    
    if request.method == 'POST':
        form = OnlinePaymentForm(request.POST, bill=bill)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.bill = bill
            payment.customer = request.user
            payment.payment_status = 'pending'
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                status='pending',
                notes='Payment initiated',
                changed_by=request.user
            )
            
            return redirect('payments:process_payment', payment_id=payment.payment_id)
    else:
        form = OnlinePaymentForm(bill=bill)
    
    return render(request, 'customer/payment.html', {'form': form, 'bill': bill})


@login_required
def process_payment(request, payment_id):
    """Process payment through selected gateway"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if payment.customer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('billing:customer_dashboard')
    
    # Payment gateway integration would go here
    # For now, we'll simulate the payment process
    
    context = {
        'payment': payment,
        'bill': payment.bill,
    }
    
    return render(request, 'payments/process.html', context)


@login_required
def payment_success(request, payment_id):
    """Payment success page"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if payment.customer != request.user and not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('billing:customer_dashboard')
    
    return render(request, 'payments/success.html', {'payment': payment})


@login_required
def payment_failed(request, payment_id):
    """Payment failed page"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if payment.customer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('billing:customer_dashboard')
    
    return render(request, 'payments/failed.html', {'payment': payment})


@login_required
def payment_history(request):
    """View payment history"""
    payments = Payment.objects.filter(customer=request.user)
    return render(request, 'customer/payment_history.html', {'payments': payments})


@login_required
def record_walk_in_payment(request, bill_id):
    """Staff record walk-in payment"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    bill = get_object_or_404(Bill, id=bill_id)
    
    if request.method == 'POST':
        form = WalkInPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.bill = bill
            payment.customer = bill.customer
            payment.payment_status = 'completed'
            payment.processed_by = request.user
            payment.processed_date = timezone.now()
            payment.save()
            
            # Update bill
            bill.amount_paid += payment.amount
            bill.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                status='completed',
                notes='Walk-in payment recorded by staff',
                changed_by=request.user
            )

            # Notify the customer via email
            try:
                if payment.customer.email:
                    send_mail(
                        subject='AWAS Payment Recorded',
                        message=(
                            f"Dear {payment.customer.get_full_name()},\n\n"
                            f"Your walk-in payment of ₱{payment.amount} for the bill ({bill.billing_month:%B %Y}) "
                            f"has been recorded successfully by our staff. Reference: {payment.reference_number}.\n\n"
                            "Thank you.\nAWAS"
                        ),
                        from_email=getattr(settings, 'EMAIL_HOST_USER', None) or 'no-reply@awas.local',
                        recipient_list=[payment.customer.email],
                        fail_silently=True,
                    )
            except Exception:
                pass
            
            messages.success(request, 'Payment recorded successfully.')
            # Redirect back to staff payments list and highlight the new payment
            return redirect(f"{reverse('payments:staff_payment_list')}?highlight={payment.payment_id}")
    else:
        form = WalkInPaymentForm(initial={
            'amount': bill.balance,
            'payment_method': 'walk_in',
        })
    
    return render(request, 'staff/record_payment.html', {'form': form, 'bill': bill})


@login_required
def staff_walk_in_create(request):
    """Staff page to search a customer and list unpaid bills for quick walk-in recording."""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    query = request.GET.get('q', '').strip()
    results = []  # list of dicts: {customer, unpaid_bills}

    if query:
        # Search by full/partial name or exact water meter id
        users = User.objects.all()
        # Name search: case-insensitive contains on first_name/last_name/username
        users = users.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(username__icontains=query) |
            models.Q(water_meter_id__iexact=query)
        )[:20]

        for u in users:
            unpaid = Bill.objects.filter(customer=u, payment_status__in=['unpaid', 'partially_paid']).order_by('due_date')
            if unpaid.exists():
                results.append({'customer': u, 'unpaid_bills': unpaid})

    context = {
        'query': query,
        'results': results,
    }

    return render(request, 'staff/record_payment.html', context)


@login_required
def verify_payment(request, payment_id):
    """Staff verify payment"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.processed_by = request.user
            payment.processed_date = timezone.now()
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                status=payment.payment_status,
                notes=form.cleaned_data.get('notes', ''),
                changed_by=request.user
            )
            
            messages.success(request, 'Payment verified successfully.')
            return redirect('payments:staff_payment_list')
    else:
        form = PaymentVerificationForm(instance=payment)
    
    return render(request, 'staff/verify_payment.html', {'form': form, 'payment': payment})


@login_required
def staff_payment_list(request):
    """List all payments for staff"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payments = Payment.objects.select_related('customer', 'bill').all()

    # Paid/Unpaid filter (maps to payment_status)
    paid_filter = request.GET.get('paid')  # expected values: 'paid', 'unpaid'
    if paid_filter == 'paid':
        payments = payments.filter(payment_status='completed')
    elif paid_filter == 'unpaid':
        payments = payments.exclude(payment_status='completed')

    # Purok filter (by customer's purok number)
    purok = request.GET.get('purok')
    if purok and purok.isdigit():
        payments = payments.filter(customer__purok_number=int(purok))

    # Prepare unpaid bills list for quick walk-in recording (respect current purok filter)
    unpaid_bills = Bill.objects.select_related('customer').filter(
        payment_status__in=['unpaid', 'partially_paid']
    )
    if purok and purok.isdigit():
        unpaid_bills = unpaid_bills.filter(customer__purok_number=int(purok))
    unpaid_bills = unpaid_bills.order_by('due_date')[:25]

    context = {
        'payments': payments,
        'current_paid': paid_filter or '',
        'current_purok': purok or '',
        'unpaid_bills': unpaid_bills,
        'purok_choices': getattr(settings, 'PUROK_CHOICES', [(i, f'Purok {i}') for i in range(1, 9)]),
    }

    return render(request, 'staff/payment_list.html', context)


# Payment Gateway Callbacks
@csrf_exempt
def gcash_callback(request):
    """Handle GCash payment callback"""
    # Implement GCash callback logic here
    # This is a placeholder for actual integration
    
    if request.method == 'POST':
        # Process GCash callback data
        # Update payment status accordingly
        pass
    
    return JsonResponse({'status': 'received'})


@csrf_exempt
def paypal_callback(request):
    """Handle PayPal payment callback"""
    # Implement PayPal callback logic here
    # This is a placeholder for actual integration
    
    if request.method == 'POST':
        # Process PayPal callback data
        # Update payment status accordingly
        pass
    
    return JsonResponse({'status': 'received'})


@csrf_exempt
def paymaya_callback(request):
    """Handle PayMaya payment callback"""
    # Implement PayMaya callback logic here
    # This is a placeholder for actual integration
    
    if request.method == 'POST':
        # Process PayMaya callback data
        # Update payment status accordingly
        pass
    
    return JsonResponse({'status': 'received'})
