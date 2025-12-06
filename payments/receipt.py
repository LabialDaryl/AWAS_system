"""
Receipt generation utilities for payments
"""
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import logging

logger = logging.getLogger(__name__)


def generate_pdf_receipt(payment):
    """
    Generate PDF receipt for payment
    
    Args:
        payment: Payment model instance
        
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0077be'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12
    )
    
    # Title
    story.append(Paragraph("AWAS Water Billing System", title_style))
    story.append(Paragraph("Payment Receipt", styles['Heading2']))
    story.append(Spacer(1, 0.3*inch))
    
    # Payment Details
    story.append(Paragraph("Payment Details", heading_style))
    
    data = [
        ['Reference Number:', payment.reference_number],
        ['Transaction ID:', payment.transaction_id or 'N/A'],
        ['Payment Date:', payment.payment_date.strftime('%B %d, %Y %I:%M %p')],
        ['Payment Method:', payment.get_payment_method_display()],
        ['Status:', payment.get_payment_status_display()],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Bill Details
    story.append(Paragraph("Bill Details", heading_style))
    bill = payment.bill
    bill_data = [
        ['Billing Month:', bill.billing_month.strftime('%B %Y')],
        ['Due Date:', bill.due_date.strftime('%B %d, %Y')],
        ['Water Consumption:', f"{bill.water_consumption} cubic meters"],
        ['Water Charge:', f"₱{bill.water_charge:.2f}"],
        ['Total Amount:', f"₱{bill.total_amount:.2f}"],
        ['Amount Paid:', f"₱{payment.amount:.2f}"],
    ]
    
    bill_table = Table(bill_data, colWidths=[2*inch, 4*inch])
    bill_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Customer Details
    story.append(Paragraph("Customer Details", heading_style))
    customer = payment.customer
    customer_data = [
        ['Name:', customer.get_full_name()],
        ['Email:', customer.email],
        ['Phone:', customer.phone_number or 'N/A'],
        ['Address:', f"Purok {customer.purok_number}, {customer.specific_address}" if customer.purok_number else customer.specific_address or 'N/A'],
    ]
    
    customer_table = Table(customer_data, colWidths=[2*inch, 4*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(customer_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Footer
    story.append(Paragraph(
        "This is an official receipt from AWAS Water Billing System. "
        "Please keep this receipt for your records.",
        styles['Normal']
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_html_receipt(payment):
    """
    Generate HTML receipt for payment
    
    Args:
        payment: Payment model instance
        
    Returns:
        str: HTML content
    """
    context = {
        'payment': payment,
        'bill': payment.bill,
        'customer': payment.customer,
    }
    return render_to_string('payments/receipt.html', context)


def send_receipt_email(payment):
    """
    Send receipt via email
    
    Args:
        payment: Payment model instance
    """
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    
    try:
        html_content = generate_html_receipt(payment)
        
        subject = f'AWAS Payment Receipt - {payment.reference_number}'
        from_email = getattr(settings, 'EMAIL_HOST_USER', 'no-reply@awas.local')
        to_email = payment.customer.email
        
        if not to_email:
            logger.warning(f"No email address for customer {payment.customer.id}")
            return False
        
        msg = EmailMultiAlternatives(subject, '', from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        
        # Attach PDF receipt
        pdf_buffer = generate_pdf_receipt(payment)
        msg.attach(
            f'receipt_{payment.reference_number}.pdf',
            pdf_buffer.read(),
            'application/pdf'
        )
        
        msg.send()
        
        # Update payment record
        payment.receipt_sent = True
        payment.receipt_sent_at = timezone.now()
        payment.save(update_fields=['receipt_sent', 'receipt_sent_at'])
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send receipt email: {str(e)}")
        return False


def send_receipt_sms(payment):
    """
    Send receipt via SMS (placeholder - integrate with SMS gateway)
    
    Args:
        payment: Payment model instance
    """
    # TODO: Integrate with SMS gateway (e.g., Twilio, Nexmo)
    # For now, this is a placeholder
    logger.info(f"SMS receipt would be sent to {payment.customer.phone_number}")
    return False

