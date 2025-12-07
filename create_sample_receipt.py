from PIL import Image, ImageDraw, ImageFont
import os

def create_sample_receipt():
    # Create a blank image with white background
    width, height = 400, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Add some text to make it look like a receipt
    text = """
    GCASH PAYMENT RECEIPT
    ====================
    
    Transaction #: GCASH-1234567890
    Date: 2025-12-07 16:00:00
    
    Amount: PHP 450.00
    
    Status: COMPLETED
    
    From: Sample Sender
    To: AWAS Billing System
    
    Reference: REF-0001-0001-1234
    
    Thank you for using GCash!
    """
    
    # Use default font
    font = ImageFont.load_default()
    
    # Draw the text
    draw.text((20, 20), text, fill='black', font=font)
    
    # Draw a border
    draw.rectangle([5, 5, width-5, height-5], outline='black')
    
    # Create the payment_proofs directory if it doesn't exist
    os.makedirs('media/payment_proofs', exist_ok=True)
    
    # Save the image
    image.save('media/payment_proofs/sample_receipt.jpg')
    print("Created sample receipt at media/payment_proofs/sample_receipt.jpg")

if __name__ == "__main__":
    create_sample_receipt()
