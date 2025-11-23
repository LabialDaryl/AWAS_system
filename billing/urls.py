from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'billing'

urlpatterns = [
    # Customer dashboard
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/bills/', views.customer_bills, name='customer_bills'),
    path('customer/bill/<int:bill_id>/', views.bill_detail, name='bill_detail'),
    
    
    # Staff dashboard
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/bills/create/', views.create_bill, name='create_bill'),
    path('staff/bills/<int:bill_id>/edit/', views.edit_bill, name='edit_bill'),
    path('staff/customers/', views.customer_list, name='customer_list'),
    path('staff/customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('staff/customers/<int:customer_id>/suspend/', views.suspend_customer, name='suspend_customer'),
    path('staff/customers/<int:customer_id>/reinstate/', views.reinstate_customer, name='reinstate_customer'),
    path('staff/membership-requests/', views.membership_requests, name='membership_requests'),
    path('staff/membership-requests/<int:request_id>/approve/', views.approve_membership, name='approve_membership'),
    path('staff/membership-requests/<int:request_id>/reject/', views.reject_membership, name='reject_membership'),
    
    # Staff extras
    path('staff/complaints/', views.staff_complaints, name='staff_complaints'),
    path('staff/reports/', views.staff_reports, name='staff_reports'),
    # Backward-compatible redirect: staff payments under billing -> payments app
    path('staff/payments/', RedirectView.as_view(url='/payments/staff/payments/', permanent=False)),
    
    # Water updates
    path('staff/water-updates/', views.water_updates_list, name='water_updates_list'),
    path('staff/water-updates/create/', views.create_water_update, name='create_water_update'),
    path('staff/water-updates/<int:update_id>/edit/', views.edit_water_update, name='edit_water_update'),
    path('staff/water-updates/<int:update_id>/delete/', views.delete_water_update, name='delete_water_update'),
    
    # Public water updates
    path('water-updates/', views.public_water_updates, name='public_water_updates'),
]
