from django import forms
from .models import Bill, WaterUpdate
from accounts.models import User


class BillCreateForm(forms.ModelForm):
    """Form for staff to create monthly bills"""
    
    class Meta:
        model = Bill
        fields = ['customer', 'billing_month', 'due_date', 'disconnection_date',
                  'previous_reading', 'present_reading']
        widgets = {
            'billing_month': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'disconnection_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        purok = kwargs.pop('purok', None)
        without_bill_this_month = kwargs.pop('without_bill_this_month', False)
        super().__init__(*args, **kwargs)
        # Only show active customers (and optionally filter by purok)
        qs = User.objects.filter(
            user_type='customer',
            is_active=True,
            is_suspended=False
        )
        if purok:
            qs = qs.filter(purok_number=purok)
        if without_bill_this_month:
            from django.utils import timezone
            from datetime import timedelta
            current_month = timezone.now().date().replace(day=1)
            next_month = (current_month + timedelta(days=32)).replace(day=1)
            qs = qs.exclude(
                bills__billing_month__gte=current_month,
                bills__billing_month__lt=next_month
            )
        self.fields['customer'].queryset = qs.order_by('last_name', 'first_name')


class BillUpdateForm(forms.ModelForm):
    """Form for staff to update bills"""
    
    class Meta:
        model = Bill
        fields = ['present_reading', 'due_date', 'disconnection_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'disconnection_date': forms.DateInput(attrs={'type': 'date'}),
        }


class BillFilterForm(forms.Form):
    """Form for filtering bills"""
    
    payment_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + Bill.PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    purok = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    month = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'month', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.conf import settings
        self.fields['purok'].choices = [('', 'All Puroks')] + list(settings.PUROK_CHOICES)


class WaterUpdateForm(forms.ModelForm):
    """Form for staff to post water updates"""
    send_to_all = forms.BooleanField(
        required=False,
        initial=True,
        label='Send to all puroks'
    )

    class Meta:
        model = WaterUpdate
        fields = ['update_type', 'content', 'priority', 'target_puroks', 'is_active']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'target_puroks': forms.TextInput(attrs={
                'placeholder': 'e.g., 1,2,3 or leave blank for all puroks'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace the free-text title with a type selector
        base_choices = [
            ('Announcements', 'Announcements'),
            ('Emergency', 'Emergency'),
            ('Maintenance', 'Maintenance'),
        ]

        # Ensure existing non-standard titles remain selectable on edit by mapping to update_type
        instance_type = getattr(getattr(self, 'instance', None), 'update_type', None)
        choices = list(base_choices)
        if instance_type and instance_type not in dict(base_choices):
            choices.append((instance_type, instance_type))

        self.fields['update_type'] = forms.ChoiceField(
            choices=choices,
            label='Type',
            widget=forms.Select(attrs={'class': 'form-select'})
        )

        # Initialize send_to_all based on existing target_puroks
        if getattr(self.instance, 'pk', None):
            self.fields['send_to_all'].initial = not bool(getattr(self.instance, 'target_puroks', '').strip())

    def clean(self):
        cleaned = super().clean()
        send_all = cleaned.get('send_to_all')
        target = (cleaned.get('target_puroks') or '').strip()

        if send_all:
            # Clear target_puroks to mean all
            cleaned['target_puroks'] = ''
        else:
            # Validate specific puroks list
            if not target:
                self.add_error('target_puroks', 'Specify at least one purok or choose "Send to all puroks".')
            else:
                # Ensure values are comma-separated digits 1..8 (but do not enforce range strictly here)
                parts = [p.strip() for p in target.split(',') if p.strip()]
                if not all(part.isdigit() for part in parts):
                    self.add_error('target_puroks', 'Puroks must be numbers separated by commas, e.g., 1,2,3.')
                cleaned['target_puroks'] = ','.join(parts)
        return cleaned
