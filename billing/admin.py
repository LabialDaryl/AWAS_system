from django.contrib import admin
from .models import Bill, WaterUpdate


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['customer', 'billing_month', 'water_consumption', 'total_amount', 
                    'amount_paid', 'balance', 'payment_status', 'due_date']
    list_filter = ['payment_status', 'billing_month', 'is_overdue']
    search_fields = ['customer__username', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['water_consumption', 'water_charge', 'total_amount', 'balance', 
                       'created_at', 'updated_at']
    date_hierarchy = 'billing_month'
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer', 'created_by')
        }),
        ('Billing Period', {
            'fields': ('billing_month', 'due_date', 'disconnection_date')
        }),
        ('Water Consumption', {
            'fields': ('previous_reading', 'present_reading', 'water_consumption')
        }),
        ('Billing Rates', {
            'fields': ('minimum_cubic_meters', 'rate_per_cubic_meter', 'minimum_charge')
        }),
        ('Amounts', {
            'fields': ('water_charge', 'total_amount', 'amount_paid', 'balance')
        }),
        ('Status', {
            'fields': ('payment_status', 'is_overdue')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(WaterUpdate)
class WaterUpdateAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'posted_by', 'posted_at', 'is_active']
    list_filter = ['priority', 'is_active', 'posted_at']
    search_fields = ['title', 'content']
    readonly_fields = ['posted_at', 'updated_at']
    
    fieldsets = (
        ('Update Information', {
            'fields': ('title', 'content', 'priority')
        }),
        ('Targeting', {
            'fields': ('target_puroks',)
        }),
        ('Status', {
            'fields': ('is_active', 'posted_by', 'posted_at', 'updated_at')
        }),
    )
