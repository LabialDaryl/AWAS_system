from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Complaint, ComplaintComment
from .forms import ComplaintForm, ComplaintResponseForm, ComplaintCommentForm


@login_required
def complaint_list(request):
    """List customer's complaints"""
    complaints = Complaint.objects.filter(customer=request.user)
    return render(request, 'complaints/list.html', {'complaints': complaints})


@login_required
def create_complaint(request):
    """Create a new complaint/suggestion"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.customer = request.user
            complaint.save()
            messages.success(request, 'Your complaint/suggestion has been submitted successfully.')
            return redirect('complaints:complaint_detail', complaint_id=complaint.id)
    else:
        form = ComplaintForm()
    
    return render(request, 'complaints/create.html', {'form': form})


@login_required
def complaint_detail(request, complaint_id):
    """View complaint details"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    # Check permissions
    if not (complaint.customer == request.user or request.user.is_staff_member):
        messages.error(request, 'You do not have permission to view this complaint.')
        return redirect('complaints:complaint_list')
    
    comment_form = ComplaintCommentForm()
    return render(request, 'complaints/detail.html', {
        'complaint': complaint,
        'comment_form': comment_form
    })


@login_required
def add_comment(request, complaint_id):
    """Add a comment to a complaint"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    # Verify permission: only the complaint owner or staff can add comments
    if complaint.customer != request.user and not request.user.is_staff_member:
        messages.error(request, 'You do not have permission to comment on this complaint.')
        return redirect('complaints:complaint_list')
    
    if request.method == 'POST':
        form = ComplaintCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.complaint = complaint
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment added successfully.')
    
    return redirect('complaints:complaint_detail', complaint_id=complaint_id)


@login_required
def staff_complaint_list(request):
    """List all complaints for staff"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    complaints = Complaint.objects.all()
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    
    return render(request, 'complaints/staff_list.html', {'complaints': complaints})


@login_required
def respond_to_complaint(request, complaint_id):
    """Staff respond to a complaint"""
    if not request.user.is_staff_member:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    if request.method == 'POST':
        form = ComplaintResponseForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.responded_by = request.user
            complaint.responded_at = timezone.now()
            complaint.save()
            messages.success(request, 'Response submitted successfully.')
            return redirect('complaints:staff_complaint_list')
    else:
        form = ComplaintResponseForm(instance=complaint)
    
    return render(request, 'complaints/respond.html', {
        'form': form,
        'complaint': complaint
    })
