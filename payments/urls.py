from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Customer payment views
    path('pay/<int:bill_id>/', views.initiate_payment, name='initiate_payment'),
    path('process/<uuid:payment_id>/', views.process_payment, name='process_payment'),
    path('success/<uuid:payment_id>/', views.payment_success, name='payment_success'),
    path('failed/<uuid:payment_id>/', views.payment_failed, name='payment_failed'),
    path('history/', views.payment_history, name='payment_history'),
    
    # Staff payment views
    path('staff/walk-in/', views.staff_walk_in_create, name='staff_walk_in_create'),
    path('staff/record/<int:bill_id>/', views.record_walk_in_payment, name='record_walk_in_payment'),
    path('staff/verify/<int:payment_id>/', views.verify_payment, name='verify_payment'),
    path('staff/payments/', views.staff_payment_list, name='staff_payment_list'),
    
    # Payment gateway callbacks
    path('callback/gcash/', views.gcash_callback, name='gcash_callback'),
    path('callback/paypal/', views.paypal_callback, name='paypal_callback'),
    path('callback/paymaya/', views.paymaya_callback, name='paymaya_callback'),
]
