from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser"""
    
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customer')
    email = models.EmailField(unique=True)
    middle_initial = models.CharField(max_length=1, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    purok_number = models.IntegerField(choices=settings.PUROK_CHOICES, null=True, blank=True)
    specific_address = models.TextField(blank=True)
    connection_type = models.CharField(
        max_length=20, 
        choices=settings.CONNECTION_TYPE_CHOICES,
        default='residential'
    )
    water_meter_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    is_active_customer = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Membership request fields
    is_membership_approved = models.BooleanField(default=False)
    membership_request_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['username']
    
    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_staff_member(self):
        return self.user_type == 'staff' or self.is_staff
    
    @property
    def has_unpaid_bills(self):
        from billing.models import Bill
        return Bill.objects.filter(customer=self, payment_status='unpaid').exists()

    @property
    def is_admin(self):
        return self.user_type == 'admin' or self.is_superuser


class MembershipRequest(models.Model):
    """Model for handling water connection membership requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    purok_number = models.IntegerField(choices=settings.PUROK_CHOICES)
    specific_address = models.TextField()
    connection_type = models.CharField(max_length=20, choices=settings.CONNECTION_TYPE_CHOICES)
    
    # Request details
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    #only admin can process not all the user appearing in the dropdown
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_requests'
    )
    notes = models.TextField(blank=True)
    
    # Created user reference (after approval)
    created_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membership_request'
    )
    
    class Meta:
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_status_display()}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
