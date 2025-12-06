from django.contrib import admin
from .models import Payment, PaymentHistory, PaymentAuditLog


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ['status', 'notes', 'changed_by', 'timestamp']
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'customer', 'bill', 'amount', 'payment_method', 
                    'payment_status', 'is_flagged', 'payment_date']
    list_filter = ['payment_status', 'payment_method', 'payment_date', 'is_flagged', 'is_disputed']
    search_fields = ['reference_number', 'customer__username', 'customer__first_name', 
                     'customer__last_name', 'gateway_transaction_id', 'transaction_id']
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
            'fields': ('gateway_transaction_id', 'transaction_id', 'webhook_id', 'gateway_response')
        }),
        ('Refund Information', {
            'fields': ('refund_requested', 'refund_requested_by', 'refund_requested_at',
                      'refund_approved', 'refund_approved_by', 'refund_approved_at',
                      'refund_amount', 'refund_transaction_id')
        }),
        ('Dispute & Flags', {
            'fields': ('is_disputed', 'is_flagged', 'flagged_by', 'flagged_at', 'flag_reason')
        }),
        ('Processing', {
            'fields': ('payment_date', 'processed_date', 'processed_by', 'notes', 'receipt_image',
                      'receipt_sent', 'receipt_sent_at')
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


@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'payment', 'user', 'user_role', 'status', 'timestamp']
    list_filter = ['action', 'user_role', 'status', 'timestamp']
    search_fields = ['payment__reference_number', 'user__username', 'user__email', 'ip_address']
    readonly_fields = ['payment', 'action', 'user', 'user_role', 'ip_address', 'user_agent', 
                      'details', 'status', 'timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('action', 'payment', 'status', 'timestamp')
        }),
        ('User Information', {
            'fields': ('user', 'user_role', 'ip_address', 'user_agent')
        }),
        ('Details', {
            'fields': ('details',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Audit logs are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are read-only
