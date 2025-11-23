from django.contrib import admin
from .models import Complaint, ComplaintComment


class ComplaintCommentInline(admin.TabularInline):
    model = ComplaintComment
    extra = 1
    readonly_fields = ['created_at']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['subject', 'customer', 'type', 'priority', 'status', 'created_at']
    list_filter = ['type', 'priority', 'status', 'created_at']
    search_fields = ['subject', 'description', 'customer__username', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['created_at', 'updated_at', 'responded_at']
    inlines = [ComplaintCommentInline]
    
    fieldsets = (
        ('Complaint Information', {
            'fields': ('customer', 'type', 'subject', 'description', 'priority', 'status', 'attachment')
        }),
        ('Response', {
            'fields': ('response', 'responded_by', 'responded_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ComplaintComment)
class ComplaintCommentAdmin(admin.ModelAdmin):
    list_display = ['complaint', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['complaint__subject', 'user__username', 'comment']
    readonly_fields = ['created_at']
