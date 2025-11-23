from django import forms
from .models import Complaint, ComplaintComment


class ComplaintForm(forms.ModelForm):
    """Form for customers to submit complaints/suggestions"""
    
    class Meta:
        model = Complaint
        fields = ['type', 'subject', 'description', 'attachment']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }


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
