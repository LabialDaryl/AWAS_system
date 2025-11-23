from django.contrib import admin
from .models import Payment, PaymentHistory


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ['status', 'notes', 'changed_by', 'timestamp']
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'customer', 'bill', 'amount', 'payment_method', 
                    'payment_status', 'payment_date']
    list_filter = ['payment_status', 'payment_method', 'payment_date']
    search_fields = ['reference_number', 'customer__username', 'customer__first_name', 
                     'customer__last_name', 'gateway_transaction_id']
    readonly_fields = ['payment_id', 'reference_number', 'created_at', 'updated_at']
    inlines = [PaymentHistoryInline]
    
    fieldsets = (
        ('Payment Identification', {
            'fields': ('payment_id', 'reference_number')
        }),
        ('Payment Details', {
            'fields': ('bill', 'customer', 'amount', 'payment_method', 'payment_status')
        }),
        ('Gateway Information', {
            'fields': ('gateway_transaction_id', 'gateway_response')
        }),
        ('Processing', {
            'fields': ('payment_date', 'processed_date', 'processed_by', 'notes', 'receipt_image')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['payment', 'status', 'changed_by', 'timestamp']
    list_filter = ['status', 'timestamp']
    search_fields = ['payment__reference_number']
    readonly_fields = ['payment', 'status', 'notes', 'changed_by', 'timestamp']
