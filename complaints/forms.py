from django import forms
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from .models import Complaint, ComplaintComment


class ComplaintForm(forms.ModelForm):
    """Form for customers to submit complaints/suggestions"""
    attachment = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])],
        help_text='Allowed formats: PDF, JPG, PNG, DOC, DOCX (Max 5MB)'
    )

    class Meta:
        model = Complaint
        fields = ['type', 'subject', 'description', 'attachment']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            if attachment.size > 5 * 1024 * 1024:
                raise ValidationError('Attachment file size cannot exceed 5MB.')
        return attachment


class ComplaintResponseForm(forms.ModelForm):
    """Form for staff to respond to complaints"""
    
    class Meta:
        model = Complaint
        fields = ['status', 'priority', 'response']
        widgets = {
            'response': forms.Textarea(attrs={'rows': 4}),
        }


class ComplaintCommentForm(forms.ModelForm):
    """Form for adding comments to complaints"""
    
    class Meta:
        model = ComplaintComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a comment...'}),
        }
