from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, MembershipRequest


class MembershipRequestForm(forms.ModelForm):
    """Form for water connection membership requests"""
    
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


class UserRegistrationForm(UserCreationForm):
    """Form for staff to create customer accounts"""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number',
                  'purok_number', 'specific_address', 'connection_type', 'password1', 'password2']
        widgets = {
            'specific_address': forms.Textarea(attrs={'rows': 3}),
        }


class CustomerSelfRegistrationForm(UserCreationForm):
    """Public self-registration form capturing required info and terms agreement"""

    middle_initial = forms.CharField(max_length=1, required=False, label='Middle Initial')
    phone_number = forms.CharField(max_length=15, required=True, label='Contact Number')
    specific_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=True)
    connection_type = forms.ChoiceField(choices=(), required=True)
    water_meter_id = forms.CharField(max_length=50, required=True, label='Water Meter ID Number')
    agree_terms = forms.BooleanField(required=True, label='I agree to the Terms and Privacy Policy')

    class Meta:
        model = User
        fields = [
            'first_name', 'middle_initial', 'last_name',
            'username', 'email', 'phone_number',
            'purok_number', 'specific_address', 'connection_type',
            'water_meter_id', 'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.conf import settings
        # populate choices
        self.fields['purok_number'] = forms.ChoiceField(choices=settings.PUROK_CHOICES, required=True)
        self.fields['connection_type'].choices = settings.CONNECTION_TYPE_CHOICES
        
        # Apply Bootstrap styling to all fields
        for field_name, field in self.fields.items():
            if field_name == 'agree_terms':
                field.widget.attrs.update({
                    'class': 'form-check-input',
                    'id': f'signup-{field_name}'
                })
            elif field_name == 'specific_address':
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'Enter your complete address',
                    'id': f'signup-{field_name}',
                    'rows': 3
                })
            elif field_name in ['purok_number', 'connection_type']:
                field.widget.attrs.update({
                    'class': 'form-select',
                    'id': f'signup-{field_name}'
                })
            else:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'id': f'signup-{field_name}'
                })
        
        # Specific placeholders and attributes
        self.fields['first_name'].widget.attrs.update({'placeholder': 'First Name'})
        self.fields['middle_initial'].widget.attrs.update({'placeholder': 'M', 'maxlength': '1'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Last Name'})
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['email'].widget.attrs.update({'placeholder': 'your@email.com', 'type': 'email'})
        self.fields['phone_number'].widget.attrs.update({'placeholder': '09XXXXXXXXX', 'type': 'tel'})
        self.fields['water_meter_id'].widget.attrs.update({'placeholder': 'Meter ID'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a strong password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})

    def clean_water_meter_id(self):
        wm = self.cleaned_data['water_meter_id']
        if User.objects.filter(water_meter_id=wm).exists():
            raise forms.ValidationError('This water meter ID is already registered.')
        return wm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'
        user.is_active = True  # allow immediate login
        # cast purok_number to int (ChoiceField returns str)
        try:
            user.purok_number = int(self.cleaned_data.get('purok_number'))
        except Exception:
            pass
        user.specific_address = self.cleaned_data.get('specific_address')
        user.connection_type = self.cleaned_data.get('connection_type')
        user.middle_initial = self.cleaned_data.get('middle_initial') or ''
        user.water_meter_id = self.cleaned_data.get('water_meter_id')
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """Custom login form with Bootstrap styling"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'id': 'login-username',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
            'id': 'login-password',
            'autocomplete': 'current-password'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'id': 'login-username',
            'autocomplete': 'username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
            'id': 'login-password',
            'autocomplete': 'current-password'
        })


class UserProfileForm(forms.ModelForm):
    """Form for users to update their profile"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 
                  'specific_address', 'profile_picture']
        widgets = {
            'specific_address': forms.Textarea(attrs={'rows': 3}),
        }


class UserSearchForm(forms.Form):
    """Form for searching registered users"""
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or username...'
        })
    )
    purok_filter = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.conf import settings
        self.fields['purok_filter'].choices = [('', 'All Puroks')] + list(settings.PUROK_CHOICES)
