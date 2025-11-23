from django.db import models
from django.conf import settings
from billing.models import Bill
import uuid


class Payment(models.Model):
    """Model for payment transactions"""
    
    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
        ('paypal', 'PayPal'),
        ('paymaya', 'PayMaya'),
        ('walk_in', 'Walk-in'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Payment identification
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reference_number = models.CharField(max_length=100, unique=True, blank=True)
    
    # Payment details
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    # Payment gateway details
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.TextField(blank=True)
    
    # Metadata
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments'
    )
    
    notes = models.TextField(blank=True)
    receipt_image = models.ImageField(upload_to='payment_receipts/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment {self.reference_number} - {self.customer.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Generate reference number if not exists
        if not self.reference_number:
            self.reference_number = f"PAY-{self.payment_id.hex[:12].upper()}"
        
        # Update bill amount_paid if payment is completed
        if self.payment_status == 'completed' and self.pk:
            old_payment = Payment.objects.filter(pk=self.pk).first()
            if old_payment and old_payment.payment_status != 'completed':
                self.bill.amount_paid += self.amount
                self.bill.save()
        
        super().save(*args, **kwargs)
    
    @property
    def is_online_payment(self):
        return self.payment_method in ['gcash', 'paypal', 'paymaya']


class PaymentHistory(models.Model):
    """Model for tracking payment history and changes"""
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Payment histories'
    
    def __str__(self):
        return f"{self.payment.reference_number} - {self.status} at {self.timestamp}"
