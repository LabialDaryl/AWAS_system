from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MembershipRequest


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'middle_initial', 'last_name', 'user_type', 'purok_number', 'water_meter_id', 'is_active_customer', 'is_suspended']
    list_filter = ['user_type', 'purok_number', 'connection_type', 'is_active_customer', 'is_suspended']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = getattr(BaseUserAdmin, 'readonly_fields', ()) + (
        'last_login', 'date_joined', 'membership_request_date'
    )
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'purok_number', 'specific_address', 'middle_initial',
                      'connection_type', 'water_meter_id', 'is_active_customer', 'is_suspended', 'profile_picture',
                      'is_membership_approved', 'membership_request_date')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'user_type', 'phone_number', 'purok_number', 'specific_address', 'middle_initial',
                      'connection_type', 'water_meter_id')
        }),
    )


@admin.register(MembershipRequest)
class MembershipRequestAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'purok_number', 'connection_type', 'status', 'request_date']
    list_filter = ['status', 'purok_number', 'connection_type', 'request_date']
    search_fields = ['first_name', 'last_name', 'email']
    readonly_fields = ['request_date', 'processed_date']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
        ('Address Information', {
            'fields': ('purok_number', 'specific_address', 'connection_type')
        }),
        ('Request Status', {
            'fields': ('status', 'request_date', 'processed_date', 'processed_by', 'notes')
        }),
    )
