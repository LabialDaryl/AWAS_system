"""
Payment views for Customer, Staff, and Admin roles
Implements secure GCash payment integration with webhook handling
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
import json
import logging

from billing.models import Bill
from .models import Payment, PaymentHistory, PaymentAuditLog, PaymentProof, PaymentAudit
from .forms import (OnlinePaymentForm, WalkInPaymentForm, PaymentVerificationForm,
                   PaymentProofForm, PaymentVerificationActionForm, PaymentAuditFilterForm)
from .gcash_service import GCashService
from .utils import log_payment_action, get_client_ip
from .receipt import generate_pdf_receipt, generate_html_receipt, send_receipt_email
from django.conf import settings
from accounts.models import User

logger = logging.getLogger(__name__)


# ==================== CUSTOMER VIEWS ====================

@login_required
def payment_instructions(request, bill_id):
    """Display GCash payment instructions and QR code"""
    if not request.user.is_customer:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check if user owns this bill
    if bill.customer != request.user:
        messages.error(request, 'You do not have permission to view this bill.')
        return redirect('billing:customer_bills')
    
    # Check if bill is already paid
    if bill.payment_status == 'paid':
        messages.info(request, 'This bill is already paid.')
        return redirect('billing:customer_bills')
    
    context = {
        'bill': bill,
        'bill_id': bill_id,
        'title': 'GCash Payment Instructions'
    }
    
    return render(request, 'payments/gcash_payment_instruction.html', context)


@login_required
def initiate_payment(request, bill_id):
    """Initiate payment for a bill - Customer only"""
    if not request.user.is_customer:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check if user owns this bill
    if bill.customer != request.user:
        messages.error(request, 'You do not have permission to pay this bill.')
        return redirect('billing:customer_bills')
    
    # Check if bill is already paid
    if bill.payment_status == 'paid':
        messages.info(request, 'This bill is already paid.')
        return redirect('billing:customer_bills')
    
    # Handle form submission
    if request.method == 'POST':
        form = OnlinePaymentForm(request.POST, bill=bill)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            
            # Check for existing payment
            existing_payment = Payment.objects.filter(
                bill=bill,
                payment_status__in=['pending', 'processing', 'pending_verification']
            ).first()
            
            if existing_payment:
                # Update existing payment with new method
                existing_payment.payment_method = payment_method
                existing_payment.save()
                payment = existing_payment
            else:
                # Create a new payment record
                payment = Payment.objects.create(
                    bill=bill,
                    customer=request.user,
                    amount=bill.total_amount,
                    payment_status='pending',
                    payment_method=payment_method,
                    created_by=request.user
                )
                # Log the payment creation
                log_payment_action(payment, 'payment_created', request.user, request)
            
            # Handle different payment methods
            if payment_method == 'gcash':
                return redirect('payments:payment_instructions', bill_id=bill_id)
            elif payment_method == 'walk_in':
                messages.info(request, 'For walk-in payments, please visit the official AWAS office to process your payment.')
                return redirect('billing:customer_bills')
            else:
                messages.error(request, 'Selected payment method is not available.')
                return redirect('payments:initiate_payment', bill_id=bill_id)
    else:
        # GET request - show the form
        form = OnlinePaymentForm(bill=bill)
    
    # Get or create payment for the template
    payment = Payment.objects.filter(
        bill=bill,
        customer=request.user,
        payment_status__in=['pending', 'processing', 'pending_verification']
    ).first()
    
    if not payment:
        payment = Payment.objects.create(
            bill=bill,
            customer=request.user,
            amount=bill.total_amount,
            payment_status='pending',
            payment_method='gcash',  # Default
            created_by=request.user
        )
        log_payment_action(payment, 'payment_created', request.user, request)
    
    context = {
        'bill': bill,
        'form': form,
        'payment': payment,
    }
    return render(request, 'payments/initiate.html', context)


@login_required
def gcash_checkout(request, payment_id):
    """Redirect customer to GCash checkout"""
    if not request.user.is_customer:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if payment.customer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('billing:customer_dashboard')
    
    if payment.payment_method != 'gcash':
        messages.error(request, 'Invalid payment method.')
        return redirect('payments:initiate_payment', bill_id=payment.bill.id)
    
    if payment.payment_status not in ['pending', 'processing']:
        messages.info(request, 'This payment has already been processed.')
        return redirect('payments:payment_history')
    
    # Initialize GCash service
    gcash = GCashService()
    
    # Create checkout session
    result = gcash.create_checkout(payment, request)
    
    if result.get('status') == 'success':
        # Update payment with transaction ID
        payment.gateway_transaction_id = result.get('transaction_id', '')
        payment.payment_status = 'processing'
        payment.save()
        
        # Log action
        log_payment_action(
            payment, 'payment_initiated', request.user, request,
            {'transaction_id': result.get('transaction_id')}
        )
        
        # Redirect to GCash checkout
        checkout_url = result.get('checkout_url')
        if checkout_url:
            return redirect(checkout_url)
        else:
            messages.error(request, 'Failed to generate checkout URL.')
            return redirect('payments:payment_failed', payment_id=payment.payment_id)
    else:
        error_msg = result.get('error', 'Unknown error occurred')
        messages.error(request, f'Failed to initiate GCash payment: {error_msg}')
        
        # Update payment status
        payment.payment_status = 'failed'
        payment.save()
        
        PaymentHistory.objects.create(
            payment=payment,
            status='failed',
            notes=f'GCash checkout failed: {error_msg}',
            changed_by=request.user
        )
        
        return redirect('payments:payment_failed', payment_id=payment.payment_id)


@login_required
def payment_success(request, payment_id):
    """Payment success page"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if payment.customer != request.user and not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('billing:customer_dashboard')
    
    # Auto-send receipt if not sent yet
    if payment.payment_status == 'completed' and not payment.receipt_sent:
        send_receipt_email(payment)
        log_payment_action(payment, 'receipt_sent', request.user, request)
    
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
    """View payment history - Customer only"""
    if not request.user.is_customer:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payments = Payment.objects.filter(
        customer=request.user
    ).select_related('bill').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(payments, 10)  # Show 10 payments per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get payment proofs for each payment
    payment_proofs = {}
    for payment in page_obj:
        try:
            # Get proof using bill field instead of payment
            proof = PaymentProof.objects.get(bill=payment.bill)
            payment_proofs[payment.id] = proof
        except PaymentProof.DoesNotExist:
            pass
    
    context = {
        'page_obj': page_obj,
        'payment_proofs': payment_proofs,
        'title': 'My Payment History'
    }
    return render(request, 'payments/history.html', context)


@login_required
def download_receipt(request, payment_id):
    """Download PDF receipt"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if payment.customer != request.user and not request.user.is_staff_member:
        raise Http404("Receipt not found")
    
    # Generate PDF
    pdf_buffer = generate_pdf_receipt(payment)
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.reference_number}.pdf"'
    
    log_payment_action(payment, 'receipt_generated', request.user, request)
    
    return response


# ==================== PAYMENT PROOF VIEWS ====================

@login_required
def submit_payment_proof(request, bill_id):
    """Submit payment proof - Customer only"""
    if not request.user.is_customer:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    bill = get_object_or_404(Bill, id=bill_id, customer=request.user)
    
    # Check if bill is already paid
    if bill.payment_status == 'paid':
        messages.info(request, 'This bill is already paid.')
        return redirect('billing:customer_bills')
    
    # Check if proof already exists for this bill
    existing_proof = PaymentProof.objects.filter(bill=bill, customer=request.user).first()
    if existing_proof:
        if existing_proof.status == 'pending':
            messages.info(request, 'You have already submitted a proof for this bill. It is pending verification.')
        elif existing_proof.status == 'verified':
            messages.info(request, 'This bill has already been verified and paid.')
        else:
            messages.info(request, 'You can submit a new proof for this bill.')
        return redirect('billing:customer_bills')
    
    if request.method == 'POST':
        form = PaymentProofForm(request.POST, request.FILES, user=request.user, bill=bill)
        if form.is_valid():
            payment_proof = form.save(commit=False)
            payment_proof.bill = bill
            payment_proof.customer = request.user
            payment_proof.status = 'pending'
            payment_proof.save()
            
            # Log the action
            log_payment_action(
                payment=None,
                action='submitted_proof',
                user=request.user,
                request=request,
                details={
                    'bill_id': bill.id,
                    'reference_number': payment_proof.reference_number,
                    'proof_id': payment_proof.id
                }
            )
            
            # TODO: Send notification email to customer and staff
            
            messages.success(request, 'Your payment proof has been submitted for verification. You will be notified once it is reviewed.')
            return redirect('billing:customer_bills')
    else:
        form = PaymentProofForm(user=request.user, bill=bill)
    
    context = {
        'form': form,
        'bill': bill,
        'title': 'Submit Payment Proof'
    }
    return render(request, 'payments/submit_proof.html', context)


@login_required
def view_payment_proof(request, proof_id):
    """View payment proof - Customer, Staff, and Admin"""
    proof = get_object_or_404(PaymentProof, id=proof_id)
    
    # Check permissions
    if not (request.user == proof.customer or request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to view this proof.')
        return redirect('core:home')
    
    context = {
        'proof': proof,
        'title': 'Payment Proof Details'
    }
    return render(request, 'payments/view_proof.html', context)


# ==================== STAFF VIEWS ====================

@login_required
def pending_payment_proofs(request):
    """List all pending payment proofs for staff verification"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    proofs = PaymentProof.objects.filter(
        status='pending'
    ).select_related('bill', 'customer').order_by('submitted_at')
    
    context = {
        'proofs': proofs,
        'title': 'Pending Payment Proofs'
    }
    return render(request, 'payments/staff/pending_proofs.html', context)


@login_required
def verify_payment_proof(request, proof_id):
    """Verify or reject a payment proof - Staff only"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    proof = get_object_or_404(PaymentProof, id=proof_id)
    
    if proof.status != 'pending':
        messages.error(request, 'This proof is not pending verification.')
        return redirect('payments:pending_payment_proofs')
    
    if request.method == 'POST':
        form = PaymentVerificationActionForm(request.POST, staff=request.user, payment_proof=proof)
        if form.is_valid():
            action = form.cleaned_data['action']
            reason = form.cleaned_data['reason']
            
            with transaction.atomic():
                # Update proof status
                proof.status = action
                proof.save()
                
                # Create PaymentAudit record
                PaymentAudit.objects.create(
                    proof=proof,
                    staff=request.user,
                    action=action,
                    reason=reason,
                    admin_override=False
                )
                
                # If verified, update bill payment status
                if action == 'verified':
                    bill = proof.bill
                    bill.amount_paid = bill.total_amount
                    bill.payment_status = 'paid'
                    bill.save()
                    
                    # Log the action
                    log_payment_action(
                        payment=None,
                        action='payment_verified',
                        user=request.user,
                        request=request,
                        details={
                            'proof_id': proof.id,
                            'bill_id': bill.id,
                            'reference_number': proof.reference_number,
                            'reason': reason
                        }
                    )
                    
                    # TODO: Send notification email to customer
                    messages.success(request, 'Payment proof has been verified. Bill has been marked as paid.')
                else:
                    # Log rejection
                    log_payment_action(
                        payment=None,
                        action='payment_rejected',
                        user=request.user,
                        request=request,
                        details={
                            'proof_id': proof.id,
                            'bill_id': proof.bill.id,
                            'reference_number': proof.reference_number,
                            'reason': reason
                        }
                    )
                    
                    # TODO: Send notification email to customer
                    messages.success(request, 'Payment proof has been rejected.')
                
                return redirect('payments:pending_payment_proofs')
    else:
        form = PaymentVerificationActionForm(staff=request.user, payment_proof=proof)
    
    context = {
        'form': form,
        'proof': proof,
        'bill': proof.bill,
        'title': 'Verify Payment Proof'
    }
    return render(request, 'payments/staff/verify_proof.html', context)


@login_required
def payment_proof_audit_logs(request):
    """View payment proof audit logs - Staff and Admin"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    logs = PaymentAudit.objects.all().select_related('proof', 'proof__bill', 'proof__customer', 'staff').order_by('-timestamp')
    
    # Apply filters
    form = PaymentAuditFilterForm(request.GET or None)
    if form.is_valid():
        if form.cleaned_data['date_from']:
            logs = logs.filter(timestamp__date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            logs = logs.filter(timestamp__date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data['action']:
            logs = logs.filter(action=form.cleaned_data['action'])
        if form.cleaned_data['admin_override']:
            logs = logs.filter(admin_override=True)
    
    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'title': 'Payment Proof Audit Logs',
        'is_admin': request.user.is_superuser
    }
    return render(request, 'payments/staff/audit_logs.html', context)


@login_required
@require_http_methods(["POST"])
def admin_override_proof(request, proof_id):
    """Admin override staff decision on payment proof - Admin only"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:home')
    
    proof = get_object_or_404(PaymentProof, id=proof_id)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')
    
    if action not in ['verified', 'rejected']:
        messages.error(request, 'Invalid action.')
        return redirect('payments:payment_proof_audit_logs')
    
    with transaction.atomic():
        # Update proof status
        old_status = proof.status
        proof.status = action
        proof.save()
        
        # Create PaymentAudit record with admin_override=True
        PaymentAudit.objects.create(
            proof=proof,
            staff=request.user,
            action=action,
            reason=f"Admin override. Previous status: {old_status}. {reason}",
            admin_override=True
        )
        
        # If verified, update bill payment status
        if action == 'verified':
            bill = proof.bill
            bill.amount_paid = bill.total_amount
            bill.payment_status = 'paid'
            bill.save()
            
            log_payment_action(
                payment=None,
                action='payment_verified',
                user=request.user,
                request=request,
                details={
                    'proof_id': proof.id,
                    'bill_id': bill.id,
                    'reference_number': proof.reference_number,
                    'reason': reason,
                    'admin_override': True
                }
            )
        else:
            # If rejected, ensure bill is not marked as paid
            bill = proof.bill
            if bill.payment_status == 'paid':
                bill.payment_status = 'unpaid'
                bill.amount_paid = 0
                bill.save()
            
            log_payment_action(
                payment=None,
                action='payment_rejected',
                user=request.user,
                request=request,
                details={
                    'proof_id': proof.id,
                    'bill_id': proof.bill.id,
                    'reference_number': proof.reference_number,
                    'reason': reason,
                    'admin_override': True
                }
            )
        
        messages.success(request, f'Payment proof has been {action} by admin override.')
    
    return redirect('payments:payment_proof_audit_logs')

@login_required
def staff_payment_list(request):
    """List all payments for staff"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payments = Payment.objects.select_related('customer', 'bill').all()
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        payments = payments.filter(payment_status=status_filter)
    
    # Payment method filter
    method_filter = request.GET.get('method', '')
    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    
    # Flagged/Disputed filter
    if request.GET.get('flagged') == 'true':
        payments = payments.filter(is_flagged=True)
    if request.GET.get('disputed') == 'true':
        payments = payments.filter(is_disputed=True)
    
    # Purok filter
    purok = request.GET.get('purok')
    if purok and purok.isdigit():
        payments = payments.filter(customer__purok_number=int(purok))
    
    # Search
    search = request.GET.get('search', '')
    if search:
        payments = payments.filter(
            Q(reference_number__icontains=search) |
            Q(transaction_id__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search)
        )
    
    payments = payments.order_by('-payment_date')
    
    # Pagination
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total': Payment.objects.count(),
        'pending': Payment.objects.filter(payment_status='pending').count(),
        'completed': Payment.objects.filter(payment_status='completed').count(),
        'failed': Payment.objects.filter(payment_status='failed').count(),
        'flagged': Payment.objects.filter(is_flagged=True).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'current_status': status_filter,
        'current_method': method_filter,
        'current_purok': purok or '',
        'search': search,
        'purok_choices': getattr(settings, 'PUROK_CHOICES', [(i, f'Purok {i}') for i in range(1, 9)]),
    }
    
    return render(request, 'payments/staff_list.html', context)


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
            old_status = payment.payment_status
            payment = form.save(commit=False)
            payment.processed_by = request.user
            payment.processed_date = timezone.now()
            
            # If verifying as completed, update bill
            if payment.payment_status == 'completed' and old_status != 'completed':
                payment.bill.amount_paid += payment.amount
                payment.bill.save()
            
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                status=payment.payment_status,
                notes=form.cleaned_data.get('notes', ''),
                changed_by=request.user
            )
            
            # Log action
            log_payment_action(
                payment, 'payment_verified', request.user, request,
                {'old_status': old_status, 'new_status': payment.payment_status}
            )
            
            messages.success(request, 'Payment verified successfully.')
            return redirect('payments:staff_payment_list')
    else:
        form = PaymentVerificationForm(instance=payment)
    
    return render(request, 'payments/staff_verify.html', {'form': form, 'payment': payment})


@login_required
@require_http_methods(["POST"])
def flag_payment(request, payment_id):
    """Staff flag suspicious payment"""
    if not request.user.is_staff_member:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    payment = get_object_or_404(Payment, id=payment_id)
    reason = request.POST.get('reason', '')
    
    payment.is_flagged = True
    payment.flagged_by = request.user
    payment.flagged_at = timezone.now()
    payment.flag_reason = reason
    payment.save()
    
    PaymentHistory.objects.create(
        payment=payment,
        status=payment.payment_status,
        notes=f'Payment flagged: {reason}',
        changed_by=request.user
    )
    
    log_payment_action(payment, 'payment_flagged', request.user, request, {'reason': reason})
    
    messages.success(request, 'Payment flagged successfully.')
    return redirect('payments:staff_payment_list')


@login_required
@require_http_methods(["POST"])
def unflag_payment(request, payment_id):
    """Staff unflag payment"""
    if not request.user.is_staff_member:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    payment.is_flagged = False
    payment.flag_reason = ''
    payment.save()
    
    PaymentHistory.objects.create(
        payment=payment,
        status=payment.payment_status,
        notes='Payment unflagged',
        changed_by=request.user
    )
    
    log_payment_action(payment, 'payment_flagged', request.user, request, {'action': 'unflag'})
    
    messages.success(request, 'Payment unflagged successfully.')
    return redirect('payments:staff_payment_list')


@login_required
def request_refund(request, payment_id):
    """Staff request refund (requires admin approval)"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.payment_status != 'completed':
        messages.error(request, 'Only completed payments can be refunded.')
        return redirect('payments:staff_payment_list')
    
    if payment.refund_requested:
        messages.info(request, 'Refund already requested for this payment.')
        return redirect('payments:staff_payment_list')
    
    if request.method == 'POST':
        refund_amount = request.POST.get('refund_amount', payment.amount)
        reason = request.POST.get('reason', '')
        
        try:
            refund_amount = float(refund_amount)
            if refund_amount > payment.amount:
                messages.error(request, 'Refund amount cannot exceed payment amount.')
                return redirect('payments:request_refund', payment_id=payment_id)
        except ValueError:
            messages.error(request, 'Invalid refund amount.')
            return redirect('payments:request_refund', payment_id=payment_id)
        
        payment.refund_requested = True
        payment.refund_requested_by = request.user
        payment.refund_requested_at = timezone.now()
        payment.refund_amount = refund_amount
        payment.notes = f"Refund requested: {reason}"
        payment.save()
        
        PaymentHistory.objects.create(
            payment=payment,
            status=payment.payment_status,
            notes=f'Refund requested: {reason}',
            changed_by=request.user
        )
        
        log_payment_action(
            payment, 'refund_requested', request.user, request,
            {'refund_amount': str(refund_amount), 'reason': reason}
        )
        
        messages.success(request, 'Refund request submitted. Waiting for admin approval.')
        return redirect('payments:staff_payment_list')
    
    return render(request, 'payments/staff_refund_request.html', {'payment': payment})


# Staff cannot initiate payments on behalf of customers - this is enforced
# They can only record walk-in payments (existing functionality)


# ==================== ADMIN VIEWS ====================

@login_required
def admin_payment_dashboard(request):
    """Admin dashboard with payment analytics"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Date range filter
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    
    payments = Payment.objects.select_related('customer', 'bill').all()
    
    if from_date:
        payments = payments.filter(payment_date__gte=from_date)
    if to_date:
        payments = payments.filter(payment_date__lte=to_date)
    
    # Revenue statistics
    revenue_stats = payments.filter(payment_status='completed').aggregate(
        total_revenue=Sum('amount'),
        total_count=Count('id')
    )
    
    # Status breakdown
    status_breakdown = payments.values('payment_status').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    # Payment method breakdown
    method_breakdown = payments.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    # Daily revenue trend (last 30 days)
    from django.db.models.functions import TruncDate
    from django.core.serializers.json import DjangoJSONEncoder
    daily_revenue = list(payments.filter(
        payment_status='completed',
        payment_date__gte=timezone.now() - timezone.timedelta(days=30)
    ).annotate(
        date=TruncDate('payment_date')
    ).values('date').annotate(
        revenue=Sum('amount'),
        count=Count('id')
    ).order_by('date'))
    
    # Failed payments
    failed_payments = payments.filter(payment_status='failed').count()
    
    # Refund statistics
    refund_stats = {
        'requested': Payment.objects.filter(refund_requested=True, refund_approved=False).count(),
        'approved': Payment.objects.filter(refund_approved=True).count(),
        'total_refunded': Payment.objects.filter(refund_approved=True).aggregate(
            total=Sum('refund_amount')
        )['total'] or 0,
    }
    
    # Flagged/Disputed payments
    flagged_count = Payment.objects.filter(is_flagged=True).count()
    disputed_count = Payment.objects.filter(is_disputed=True).count()
    
    # Serialize data for JSON in template
    import json
    daily_revenue_json = json.dumps(list(daily_revenue), cls=DjangoJSONEncoder)
    status_breakdown_json = json.dumps(list(status_breakdown), cls=DjangoJSONEncoder)
    method_breakdown_json = json.dumps(list(method_breakdown), cls=DjangoJSONEncoder)
    
    context = {
        'revenue_stats': revenue_stats,
        'status_breakdown': list(status_breakdown),
        'method_breakdown': list(method_breakdown),
        'daily_revenue': daily_revenue_json,
        'daily_revenue_list': list(daily_revenue),  # For iteration if needed
        'status_breakdown_json': status_breakdown_json,
        'method_breakdown_json': method_breakdown_json,
        'failed_payments': failed_payments,
        'refund_stats': refund_stats,
        'flagged_count': flagged_count,
        'disputed_count': disputed_count,
        'from_date': from_date,
        'to_date': to_date,
    }
    
    return render(request, 'payments/admin_dashboard.html', context)


@login_required
def approve_refund(request, payment_id):
    """Admin approve refund request"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if not payment.refund_requested:
        messages.error(request, 'No refund request found for this payment.')
        return redirect('payments:admin_payment_dashboard')
    
    if payment.refund_approved:
        messages.info(request, 'Refund already approved.')
        return redirect('payments:admin_payment_dashboard')
    
    if request.method == 'POST':
        # Process refund via GCash API if it's a GCash payment
        if payment.payment_method == 'gcash' and payment.transaction_id:
            gcash = GCashService()
            result = gcash.process_refund(payment, payment.refund_amount)
            
            if result.get('status') == 'success':
                payment.refund_approved = True
                payment.refund_approved_by = request.user
                payment.refund_approved_at = timezone.now()
                payment.refund_transaction_id = result.get('refund_transaction_id', '')
                payment.payment_status = 'refunded'
                payment.save()
                
                PaymentHistory.objects.create(
                    payment=payment,
                    status='refunded',
                    notes='Refund approved and processed',
                    changed_by=request.user
                )
                
                log_payment_action(
                    payment, 'refund_approved', request.user, request,
                    {'refund_transaction_id': payment.refund_transaction_id}
                )
                
                messages.success(request, 'Refund approved and processed successfully.')
            else:
                error_msg = result.get('error', 'Unknown error')
                messages.error(request, f'Failed to process refund: {error_msg}')
                return redirect('payments:approve_refund', payment_id=payment_id)
        else:
            # For non-GCash payments, just mark as approved
            payment.refund_approved = True
            payment.refund_approved_by = request.user
            payment.refund_approved_at = timezone.now()
            payment.payment_status = 'refunded'
            payment.save()
            
            PaymentHistory.objects.create(
                payment=payment,
                status='refunded',
                notes='Refund approved (manual processing)',
                changed_by=request.user
            )
            
            log_payment_action(payment, 'refund_approved', request.user, request)
            messages.success(request, 'Refund approved.')
        
        return redirect('payments:admin_payment_dashboard')
    
    return render(request, 'payments/admin_approve_refund.html', {'payment': payment})


@login_required
def reject_refund(request, payment_id):
    """Admin reject refund request"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        payment.refund_requested = False
        payment.refund_amount = None
        payment.notes = f"Refund rejected: {reason}"
        payment.save()
        
        PaymentHistory.objects.create(
            payment=payment,
            status=payment.payment_status,
            notes=f'Refund rejected: {reason}',
            changed_by=request.user
        )
        
        log_payment_action(payment, 'refund_rejected', request.user, request, {'reason': reason})
        
        messages.success(request, 'Refund request rejected.')
        return redirect('payments:admin_payment_dashboard')
    
    return render(request, 'payments/admin_reject_refund.html', {'payment': payment})


@login_required
def audit_logs(request):
    """View payment audit logs"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    logs = PaymentAuditLog.objects.select_related('payment', 'user').all()
    
    # Filter by action
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    # Filter by user role
    role_filter = request.GET.get('role', '')
    if role_filter:
        logs = logs.filter(user_role=role_filter)
    
    logs = logs.order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_choices': PaymentAuditLog.ACTION_CHOICES,
        'current_action': action_filter,
        'current_role': role_filter,
    }
    
    return render(request, 'payments/admin_audit_logs.html', context)


# ==================== WEBHOOK HANDLERS ====================

@csrf_exempt
@require_http_methods(["POST"])
def gcash_webhook(request):
    """
    Handle GCash webhook with signature validation and idempotency
    """
    try:
        # Get webhook data
        payload = json.loads(request.body)
        signature = request.META.get('HTTP_X_GCASH_SIGNATURE', '')
        timestamp = request.META.get('HTTP_X_GCASH_TIMESTAMP', '')
        webhook_id = payload.get('webhook_id', '')
        
        # Initialize GCash service
        gcash = GCashService()
        
        # Verify signature
        if not gcash.verify_webhook_signature(payload, signature, timestamp):
            logger.warning(f"Invalid webhook signature: {webhook_id}")
            log_payment_action(
                None, 'webhook_received', None, request,
                {'error': 'Invalid signature', 'webhook_id': webhook_id}
            )
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Extract transaction details
        transaction_id = payload.get('transaction_id', '')
        reference_number = payload.get('reference_number', '')
        status = payload.get('status', '').lower()
        
        # Find payment by transaction_id or reference_number
        payment = None
        if transaction_id:
            payment = Payment.objects.filter(transaction_id=transaction_id).first()
        if not payment and reference_number:
            payment = Payment.objects.filter(reference_number=reference_number).first()
        
        if not payment:
            logger.warning(f"Payment not found for webhook: {webhook_id}")
            log_payment_action(
                None, 'webhook_received', None, request,
                {'error': 'Payment not found', 'webhook_id': webhook_id, 'transaction_id': transaction_id}
            )
            return JsonResponse({'error': 'Payment not found'}, status=404)
        
        # Check idempotency - prevent duplicate processing
        if payment.webhook_id == webhook_id and payment.payment_status == 'completed':
            logger.info(f"Webhook already processed: {webhook_id}")
            return JsonResponse({'status': 'already_processed'})
        
        # Update payment based on webhook status
        with transaction.atomic():
            old_status = payment.payment_status
            
            if status == 'success' or status == 'completed':
                payment.payment_status = 'completed'
                payment.transaction_id = transaction_id or payment.transaction_id
                payment.processed_date = timezone.now()
                
                # Update bill
                if old_status != 'completed':
                    payment.bill.amount_paid += payment.amount
                    payment.bill.save()
                
                # Send receipt
                if not payment.receipt_sent:
                    send_receipt_email(payment)
                
            elif status == 'failed':
                payment.payment_status = 'failed'
            elif status == 'cancelled':
                payment.payment_status = 'cancelled'
            
            payment.webhook_id = webhook_id
            payment.gateway_response = json.dumps(payload)
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                status=payment.payment_status,
                notes=f'Webhook received: {status}',
                changed_by=None
            )
            
            # Log action
            log_payment_action(
                payment, 'webhook_received', None, request,
                {
                    'webhook_id': webhook_id,
                    'status': status,
                    'old_status': old_status,
                    'new_status': payment.payment_status
                }
            )
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        log_payment_action(
            None, 'webhook_received', None, request,
            {'error': str(e)}
        )
        return JsonResponse({'error': 'Internal error'}, status=500)


# Keep existing walk-in payment views
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
            
            # Log action
            log_payment_action(payment, 'payment_completed', request.user, request)
            
            # Send receipt
            send_receipt_email(payment)
            
            messages.success(request, 'Payment recorded successfully.')
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
    results = []

    if query:
        users = User.objects.all()
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(water_meter_id__iexact=query)
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


# Legacy callback endpoints (kept for compatibility)
@csrf_exempt
def gcash_callback(request):
    """Legacy GCash callback - redirects to webhook"""
    return gcash_webhook(request)


@csrf_exempt
def paypal_callback(request):
    """Handle PayPal payment callback"""
    # Placeholder for PayPal integration
    return JsonResponse({'status': 'received'})


@csrf_exempt
def paymaya_callback(request):
    """Handle PayMaya payment callback"""
    # Placeholder for PayMaya integration
    return JsonResponse({'status': 'received'})


def check_payment_status(request, payment_id):
    """Check payment status manually for pending payments"""
    try:
        payment = get_object_or_404(Payment, payment_id=payment_id)
        
        # Verify user has permission to check this payment
        if request.user.is_authenticated and not request.user.is_staff and payment.customer != request.user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Permission denied'}, status=403)
            messages.error(request, 'You do not have permission to view this payment.')
            return redirect('core:home')
            
        if payment.payment_status in ['completed', 'failed', 'cancelled']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': payment.payment_status,
                    'message': f'Payment is already {payment.get_payment_status_display()}' 
                })
            messages.info(request, f"Payment is already {payment.get_payment_status_display()}.")
            return redirect('payments:payment_history')
        
        gcash = GCashService()
        if payment.gateway_transaction_id:
            result = gcash.get_transaction_status(payment.gateway_transaction_id)
            logger.debug(f"Payment status check result: {result}")
            
            if result.get('status') == 'success':
                data = result.get('data', {})
                status = data.get('status', '').lower()
                
                with transaction.atomic():
                    old_status = payment.payment_status
                    
                    if status in ['success', 'completed']:
                        payment.payment_status = 'completed'
                        payment.transaction_id = payment.transaction_id or data.get('transaction_id', '')
                        payment.processed_date = timezone.now()
                        
                        # Update bill if not already updated
                        if old_status not in ['completed', 'success']:
                            payment.bill.amount_paid += payment.amount
                            payment.bill.save()
                        
                        # Send receipt if not sent
                        if not payment.receipt_sent:
                            send_receipt_email(payment)
                        
                        message = "Payment completed successfully!"
                        
                    elif status == 'failed':
                        payment.payment_status = 'failed'
                        message = "Payment failed. Please try again."
                        
                    elif status == 'cancelled':
                        payment.payment_status = 'cancelled'
                        message = "Payment was cancelled."
                        
                    else:
                        message = f"Payment is still {status}."
                    
                    # Save payment changes
                    payment.gateway_response = json.dumps(data)
                    payment.save()
                    
                    # Log the status check
                    PaymentHistory.objects.create(
                        payment=payment,
                        status=payment.payment_status,
                        notes=f'Status checked manually: {status}',
                        changed_by=request.user if request.user.is_authenticated else None
                    )
                    
                    log_payment_action(
                        payment, 'status_checked', request.user, request,
                        {'old_status': old_status, 'new_status': payment.payment_status}
                    )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': payment.payment_status,
                        'message': message,
                        'redirect': reverse('payments:payment_history')
                    })
                
                messages.success(request, message) if payment.payment_status == 'completed' else messages.info(request, message)
                return redirect('payments:payment_history')
            
            error_msg = result.get('error', 'Unknown error occurred while checking payment status')
            logger.error(f"Payment status check failed: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=400)
                
            messages.error(request, f"Error checking payment status: {error_msg}")
            return redirect('payments:payment_history')
            
        else:
            error_msg = "No transaction ID found for this payment."
            logger.warning(f"{error_msg} Payment ID: {payment_id}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=400)
                
            messages.warning(request, error_msg)
            return redirect('payments:payment_history')
            
    except Exception as e:
        error_msg = f"Error checking payment status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Internal server error'}, status=500)
            
        messages.error(request, 'An error occurred while checking the payment status.')
        return redirect('payments:payment_history')
