from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'payments'

urlpatterns = [
    # Customer payment views
    path('instructions/<int:bill_id>/', login_required(views.payment_instructions), name='payment_instructions'),
    path('pay/<int:bill_id>/', views.initiate_payment, name='initiate_payment'),
    path('proof/submit/<int:bill_id>/', views.submit_payment_proof, name='submit_payment_proof'),
    path('proof/view/<int:proof_id>/', views.view_payment_proof, name='view_payment_proof'),
    path('status/<uuid:payment_id>/', views.check_payment_status, name='check_payment_status'),
    path('gcash/checkout/<uuid:payment_id>/', views.gcash_checkout, name='gcash_checkout'),
    path('success/<uuid:payment_id>/', views.payment_success, name='payment_success'),
    path('failed/<uuid:payment_id>/', views.payment_failed, name='payment_failed'),
    path('history/', views.payment_history, name='payment_history'),
    path('receipt/<uuid:payment_id>/', views.download_receipt, name='download_receipt'),
    
    # Staff payment views
    path('staff/proofs/pending/', views.pending_payment_proofs, name='pending_payment_proofs'),
    path('staff/proofs/verify/<int:proof_id>/', views.verify_payment_proof, name='verify_payment_proof'),
    path('staff/proofs/audit-logs/', views.payment_proof_audit_logs, name='payment_proof_audit_logs'),
    path('admin/proofs/override/<int:proof_id>/', views.admin_override_proof, name='admin_override_proof'),
    path('staff/walk-in/', views.staff_walk_in_create, name='staff_walk_in_create'),
    path('staff/record/<int:bill_id>/', views.record_walk_in_payment, name='record_walk_in_payment'),
    path('staff/verify/<int:payment_id>/', views.verify_payment, name='verify_payment'),
    path('staff/payments/', views.staff_payment_list, name='staff_payment_list'),
    path('staff/flag/<int:payment_id>/', views.flag_payment, name='flag_payment'),
    path('staff/unflag/<int:payment_id>/', views.unflag_payment, name='unflag_payment'),
    path('staff/refund/<int:payment_id>/', views.request_refund, name='request_refund'),
    
    # Admin payment views
    path('admin/dashboard/', views.admin_payment_dashboard, name='admin_dashboard'),
    path('admin/refund/approve/<int:payment_id>/', views.approve_refund, name='approve_refund'),
    path('admin/refund/reject/<int:payment_id>/', views.reject_refund, name='reject_refund'),
    path('admin/audit-logs/', views.audit_logs, name='audit_logs'),
    
    # Payment gateway webhooks
    path('webhook/gcash/', views.gcash_webhook, name='gcash_webhook'),
    path('callback/gcash/', views.gcash_callback, name='gcash_callback'),  # Legacy
    path('callback/paypal/', views.paypal_callback, name='paypal_callback'),
    path('callback/paymaya/', views.paymaya_callback, name='paymaya_callback'),
]
