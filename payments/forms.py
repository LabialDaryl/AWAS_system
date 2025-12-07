import os
import uuid
from django import forms
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Payment, PaymentProof, PaymentAudit, PaymentAuditLog


class OnlinePaymentForm(forms.ModelForm):
    """Form for online payments"""
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method']
        widgets = {
            'payment_method': forms.RadioSelect(
                choices=[
                    ('gcash', 'GCash'),
                    ('paypal', 'PayPal'),
                    ('paymaya', 'PayMaya'),
                ]
            ),
        }
    
    def __init__(self, *args, **kwargs):
        bill = kwargs.pop('bill', None)
        super().__init__(*args, **kwargs)
        
        if bill:
            self.fields['amount'].initial = bill.balance
            self.fields['amount'].widget.attrs['readonly'] = True


class WalkInPaymentForm(forms.ModelForm):
    """Form for staff to record walk-in payments"""
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'notes', 'receipt_image']
        widgets = {
            'payment_method': forms.Select(
                choices=[
                    ('walk_in', 'Walk-in Cash'),
                    ('bank_transfer', 'Bank Transfer'),
                ]
            ),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter any additional notes about this payment'}),
        }


class PaymentVerificationForm(forms.ModelForm):
    """Form for staff to verify payments"""
    
    class Meta:
        model = Payment
        fields = ['payment_status', 'notes']
        widgets = {
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter verification notes',
                'class': 'form-control'
            }),
        }


class PaymentProofForm(forms.ModelForm):
    """Form for customers to submit payment proof"""
    
    class Meta:
        from .models import PaymentProof
        model = PaymentProof
        fields = ['reference_number', 'transaction_id', 'screenshot', 'notes']
        widgets = {
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter GCash reference number',
                'required': 'required'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter GCash transaction ID (optional)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any additional information about this payment (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.bill = kwargs.pop('bill', None)
        super().__init__(*args, **kwargs)
    
    def clean_reference_number(self):
        reference_number = self.cleaned_data.get('reference_number')
        if not reference_number:
            raise forms.ValidationError('Reference number is required.')
        return reference_number
    
    def clean_screenshot(self):
        screenshot = self.cleaned_data.get('screenshot')
        if not screenshot:
            raise forms.ValidationError('Screenshot is required.')
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png']
        ext = os.path.splitext(screenshot.name)[1].lower()
        if ext not in valid_extensions:
            raise forms.ValidationError('Only JPG, JPEG, and PNG files are allowed.')
        
        # Validate file size (2MB limit)
        if screenshot.size > 2 * 1024 * 1024:
            raise forms.ValidationError('File size must be no more than 2MB.')
        
        # Rename file to prevent overwriting
        filename = f"payment_proof_{uuid.uuid4().hex}{ext}"
        screenshot.name = filename
        
        return screenshot


class PaymentVerificationActionForm(forms.Form):
    """Form for staff to verify or reject payment proofs"""
    
    ACTION_CHOICES = [
        ('verified', 'Verify Payment'),
        ('rejected', 'Reject Payment'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter reason for verification or rejection',
            'required': 'required'
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        self.staff = kwargs.pop('staff', None)
        self.payment_proof = kwargs.pop('payment_proof', None)
        super().__init__(*args, **kwargs)


class PaymentAuditFilterForm(forms.Form):
    """Form for filtering payment audit logs"""
    
    ACTION_CHOICES = [
        ('', 'All Actions'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('admin_override', 'Admin Override'),
    ]
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    admin_override = forms.BooleanField(
        required=False,
        label='Show admin overrides only',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
