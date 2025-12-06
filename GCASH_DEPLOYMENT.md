# GCash Payment Integration - Deployment Guide

This guide provides instructions for deploying and configuring the GCash payment integration in the AWAS water billing system.

## Prerequisites

- Django 4.2.7+
- Python 3.8+
- GCash Merchant Account with API credentials
- HTTPS-enabled server (required for webhooks)
- Email server configured for receipt delivery

## Environment Variables

Add the following environment variables to your `.env` file:

```env
# GCash API Configuration
GCASH_API_KEY=your_gcash_api_key_here
GCASH_API_SECRET=your_gcash_api_secret_here
GCASH_MERCHANT_ID=your_gcash_merchant_id_here
GCASH_SANDBOX=True  # Set to False for production

# Email Configuration (for receipts)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_email_password

# Security
SECRET_KEY=your_secret_key_here
DEBUG=False  # Set to False in production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# HTTPS (Required for webhooks)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Database Migration

Run migrations to create the new payment models:

```bash
python manage.py makemigrations payments
python manage.py migrate
```

## GCash API Setup

### 1. Obtain GCash API Credentials

1. Log in to your GCash Merchant Dashboard
2. Navigate to API Settings
3. Generate API Key and Secret
4. Note your Merchant ID

### 2. Configure Webhook URL

In your GCash Merchant Dashboard, set the webhook URL to:

```
https://yourdomain.com/payments/webhook/gcash/
```

**Important:** 
- Webhook URL must use HTTPS
- Webhook URL must be publicly accessible
- GCash will send webhooks to this URL for payment status updates

### 3. Test Webhook (Sandbox)

1. Use GCash sandbox environment for testing
2. Make a test payment
3. Verify webhook is received and processed
4. Check audit logs to confirm webhook processing

## Security Configuration

### 1. HTTPS Configuration

Ensure your server is configured with SSL/TLS certificates. For production:

```python
# In settings.py (already configured)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 2. Webhook Signature Validation

The system automatically validates webhook signatures using HMAC-SHA256. Ensure:

- `GCASH_API_SECRET` is kept secure
- Never expose API secret in logs or version control
- Use environment variables for all sensitive data

### 3. CSRF Protection

All payment forms are protected with Django's CSRF middleware. Ensure:

```python
# In settings.py (already configured)
MIDDLEWARE = [
    ...
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]
```

## Role-Based Access Control

The system enforces role-based access:

- **Customers**: Can initiate payments, view history, download receipts
- **Staff**: Can verify payments, flag suspicious transactions, request refunds
- **Admin**: Can approve refunds, view analytics, access audit logs

### Testing RBAC

```bash
# Run RBAC tests
python manage.py test payments.tests.PaymentViewsTest
```

## Payment Flow

### Customer Payment Flow

1. Customer selects bill to pay
2. Customer chooses GCash as payment method
3. System creates payment record with status 'pending'
4. System redirects to GCash checkout
5. Customer completes payment on GCash
6. GCash sends webhook to system
7. System updates payment status to 'completed'
8. System generates and sends receipt via email

### Webhook Processing

1. GCash sends POST request to `/payments/webhook/gcash/`
2. System validates webhook signature
3. System checks idempotency (prevents duplicate processing)
4. System updates payment status
5. System updates bill amount_paid
6. System sends receipt email
7. System logs action to audit log

## Monitoring and Logging

### Audit Logs

All payment actions are logged to `PaymentAuditLog`:

- Payment creation
- Payment status changes
- Refund requests and approvals
- Webhook processing
- Receipt generation

Access audit logs:
```
https://yourdomain.com/payments/admin/audit-logs/
```

### Error Handling

- Failed payments are logged with error details
- Webhook failures are logged to audit logs
- Email delivery failures are logged but don't block payment processing

## Testing

### Unit Tests

Run all payment tests:

```bash
python manage.py test payments
```

### Manual Testing Checklist

- [ ] Customer can initiate GCash payment
- [ ] Redirect to GCash checkout works
- [ ] Webhook is received and processed
- [ ] Payment status updates correctly
- [ ] Receipt is generated and sent
- [ ] Staff can verify payments
- [ ] Staff can flag suspicious payments
- [ ] Staff can request refunds
- [ ] Admin can approve refunds
- [ ] Admin dashboard shows analytics
- [ ] Audit logs record all actions

## Production Deployment

### 1. Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] HTTPS enabled and working
- [ ] Webhook URL configured in GCash dashboard
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] Email server configured and tested
- [ ] GCash API credentials verified
- [ ] `GCASH_SANDBOX=False` for production

### 2. Deployment Steps

```bash
# 1. Set production environment variables
export GCASH_SANDBOX=False
export DEBUG=False

# 2. Run migrations
python manage.py migrate

# 3. Collect static files
python manage.py collectstatic --noinput

# 4. Restart application server
# (depends on your deployment setup)

# 5. Verify webhook endpoint
curl -X POST https://yourdomain.com/payments/webhook/gcash/
```

### 3. Post-Deployment Verification

1. Make a test payment in production
2. Verify webhook is received
3. Check payment status is updated
4. Verify receipt is sent
5. Check audit logs
6. Verify admin dashboard shows data

## Troubleshooting

### Webhook Not Received

1. Check webhook URL is correct in GCash dashboard
2. Verify HTTPS is enabled
3. Check server logs for incoming requests
4. Verify firewall allows incoming POST requests
5. Check webhook signature validation

### Payment Status Not Updating

1. Check webhook is being received
2. Verify webhook signature validation
3. Check database for payment record
4. Review audit logs for errors
5. Check application logs

### Receipt Not Sent

1. Verify email configuration
2. Check email server logs
3. Verify customer email address is valid
4. Check `receipt_sent` flag in payment record
5. Review email delivery logs

## Support

For issues or questions:

1. Check audit logs for error details
2. Review application logs
3. Contact GCash support for API issues
4. Review Django documentation for framework issues

## Compliance

This implementation follows BSP (Bangko Sentral ng Pilipinas) guidelines:

- All transactions are logged
- Audit trail is maintained
- Secure payment processing
- Customer data protection
- Transaction reconciliation support

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [GCash API Documentation](https://developer.gcash.com/)
- [BSP Guidelines](https://www.bsp.gov.ph/)

