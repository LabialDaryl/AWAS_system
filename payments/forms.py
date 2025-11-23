from django import forms
from .models import Payment


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
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class PaymentVerificationForm(forms.ModelForm):
    """Form for staff to verify payments"""
    
    class Meta:
        model = Payment
        fields = ['payment_status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
