from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Bill(models.Model):
    """Model for monthly water bills"""
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partially_paid', 'Partially Paid'),
    ]
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bills'
    )
    
    # Billing period
    billing_month = models.DateField()
    due_date = models.DateField()
    disconnection_date = models.DateField()
    
    # Water consumption
    previous_reading = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    present_reading = models.DecimalField(max_digits=10, decimal_places=2)
    water_consumption = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    # Billing amounts
    minimum_cubic_meters = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=settings.MINIMUM_CUBIC_METERS
    )
    rate_per_cubic_meter = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=settings.RATE_PER_CUBIC_METER
    )
    minimum_charge = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=settings.MINIMUM_CHARGE
    )
    
    # Calculated amounts
    water_charge = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    # Status
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='unpaid'
    )
    is_overdue = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bills'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-billing_month']
        unique_together = ['customer', 'billing_month']
    
    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.billing_month.strftime('%B %Y')}"
    
    def save(self, *args, **kwargs):
        # Ensure Decimal arithmetic throughout
        prev = Decimal(self.previous_reading or 0)
        pres = Decimal(self.present_reading or 0)
        min_cm = Decimal(self.minimum_cubic_meters or 0)
        rate = Decimal(self.rate_per_cubic_meter or 0)
        min_charge = Decimal(self.minimum_charge or 0)
        paid = Decimal(self.amount_paid or 0)

        # Calculate water consumption
        self.water_consumption = pres - prev
        
        # Calculate water charge
        if self.water_consumption <= min_cm:
            self.water_charge = min_charge
        else:
            excess = self.water_consumption - min_cm
            self.water_charge = min_charge + (excess * rate)
        
        # Calculate total amount (no penalties)
        self.total_amount = Decimal(self.water_charge)
        
        # Calculate balance
        self.balance = Decimal(self.total_amount) - paid
        
        # Update payment status
        if self.balance <= 0:
            self.payment_status = 'paid'
        elif self.amount_paid > 0:
            self.payment_status = 'partially_paid'
        elif timezone.now().date() > self.due_date:
            self.payment_status = 'overdue'
            self.is_overdue = True
        else:
            self.payment_status = 'unpaid'
        
        super().save(*args, **kwargs)
    
    @property
    def is_due_soon(self):
        """Check if bill is due within notification period"""
        days_until_due = (self.due_date - timezone.now().date()).days
        return 0 < days_until_due <= settings.NOTIFICATION_DAYS_BEFORE_DUE
    
    @property
    def is_disconnection_soon(self):
        """Check if disconnection is imminent"""
        days_until_disconnection = (self.disconnection_date - timezone.now().date()).days
        return 0 < days_until_disconnection <= settings.NOTIFICATION_DAYS_BEFORE_DISCONNECTION


class WaterUpdate(models.Model):
    """Model for water service updates and announcements"""
    
    TYPE_CHOICES = [
        ('Announcements', 'Announcements'),
        ('Emergency', 'Emergency'),
        ('Maintenance', 'Maintenance'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Kept for compatibility; prefer using update_type going forward
    title = models.CharField(max_length=200, blank=True)
    update_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Announcements')
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Targeting
    target_puroks = models.CharField(
        max_length=50,
        blank=True,
        help_text="Comma-separated purok numbers (e.g., 1,2,3) or leave blank for all"
    )
    
    # Metadata
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='water_updates'
    )
    posted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-posted_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    def get_target_puroks_list(self):
        """Return list of target purok numbers"""
        if not self.target_puroks:
            return list(range(1, 9))  # All puroks
        return [int(p.strip()) for p in self.target_puroks.split(',') if p.strip().isdigit()]
