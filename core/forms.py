from django import forms
from accounts.models import MembershipRequest


class ConnectionRequestForm(forms.ModelForm):
    """Form for water connection requests from landing page"""
    
    agree_terms = forms.BooleanField(
        required=True,
        label="I agree to the terms and conditions"
    )
    
    class Meta:
        model = MembershipRequest
        fields = ['first_name', 'last_name', 'email', 'phone_number', 
                  'purok_number', 'specific_address', 'connection_type']
        widgets = {
            'specific_address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.conf import settings
        
        # Apply Bootstrap styling to all fields
        for field_name, field in self.fields.items():
            if field_name == 'agree_terms':
                field.widget.attrs.update({
                    'class': 'form-check-input',
                    'id': f'membership-{field_name}'
                })
            elif field_name == 'specific_address':
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'Enter your complete address',
                    'id': f'membership-{field_name}',
                    'rows': 3
                })
            elif field_name in ['purok_number', 'connection_type']:
                field.widget.attrs.update({
                    'class': 'form-select',
                    'id': f'membership-{field_name}'
                })
            else:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'id': f'membership-{field_name}'
                })
        
        # Specific placeholders and attributes
        self.fields['first_name'].widget.attrs.update({'placeholder': 'First Name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Last Name'})
        self.fields['email'].widget.attrs.update({'placeholder': 'your@email.com', 'type': 'email'})
        self.fields['phone_number'].widget.attrs.update({'placeholder': '09XXXXXXXXX', 'type': 'tel'})
        
        # Set choices for select fields
        self.fields['purok_number'].choices = [('', 'Select Purok')] + list(settings.PUROK_CHOICES)
        self.fields['connection_type'].choices = [('', 'Select Connection Type')] + list(settings.CONNECTION_TYPE_CHOICES)
