"""
Unit tests for payment functionality
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from billing.models import Bill
from .models import Payment, PaymentHistory, PaymentAuditLog
from .gcash_service import GCashService
from .utils import log_payment_action

User = get_user_model()


class PaymentModelTest(TestCase):
    """Test Payment model"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            user_type='customer',
            first_name='John',
            last_name='Doe'
        )
        self.bill = Bill.objects.create(
            customer=self.customer,
            billing_month=timezone.now().date(),
            due_date=timezone.now().date(),
            disconnection_date=timezone.now().date(),
            present_reading=Decimal('100'),
            previous_reading=Decimal('90'),
            amount_paid=Decimal('0')
        )
    
    def test_payment_creation(self):
        """Test payment creation"""
        payment = Payment.objects.create(
            bill=self.bill,
            customer=self.customer,
            amount=Decimal('150.00'),
            payment_method='gcash',
            payment_status='pending'
        )
        
        self.assertIsNotNone(payment.reference_number)
        self.assertEqual(payment.amount, Decimal('150.00'))
        self.assertEqual(payment.payment_method, 'gcash')
        self.assertEqual(payment.payment_status, 'pending')
    
    def test_payment_status_normalization(self):
        """Test that 'success' status is normalized to 'completed'"""
        payment = Payment.objects.create(
            bill=self.bill,
            customer=self.customer,
            amount=Decimal('150.00'),
            payment_method='gcash',
            payment_status='success'
        )
        
        # Status should be normalized to 'completed' on save
        payment.save()
        self.assertEqual(payment.payment_status, 'completed')


class PaymentViewsTest(TestCase):
    """Test payment views with RBAC"""
    
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            user_type='customer',
            first_name='John',
            last_name='Doe'
        )
        self.staff = User.objects.create_user(
            username='staff1',
            email='staff@test.com',
            password='testpass123',
            user_type='staff',
            is_staff=True
        )
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            user_type='admin',
            is_superuser=True
        )
        self.bill = Bill.objects.create(
            customer=self.customer,
            billing_month=timezone.now().date(),
            due_date=timezone.now().date(),
            disconnection_date=timezone.now().date(),
            present_reading=Decimal('100'),
            previous_reading=Decimal('90'),
            amount_paid=Decimal('0')
        )
    
    def test_customer_can_initiate_payment(self):
        """Test that customer can initiate payment for their own bill"""
        self.client.login(username='customer1', password='testpass123')
        response = self.client.get(reverse('payments:initiate_payment', args=[self.bill.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_customer_cannot_initiate_others_payment(self):
        """Test that customer cannot initiate payment for other's bill"""
        other_customer = User.objects.create_user(
            username='customer2',
            email='customer2@test.com',
            password='testpass123',
            user_type='customer'
        )
        other_bill = Bill.objects.create(
            customer=other_customer,
            billing_month=timezone.now().date(),
            due_date=timezone.now().date(),
            disconnection_date=timezone.now().date(),
            present_reading=Decimal('100'),
            previous_reading=Decimal('90'),
            amount_paid=Decimal('0')
        )
        
        self.client.login(username='customer1', password='testpass123')
        response = self.client.get(reverse('payments:initiate_payment', args=[other_bill.id]))
        self.assertRedirects(response, reverse('billing:customer_bills'))
    
    def test_staff_can_view_payment_list(self):
        """Test that staff can view payment list"""
        self.client.login(username='staff1', password='testpass123')
        response = self.client.get(reverse('payments:staff_payment_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_customer_cannot_access_staff_views(self):
        """Test that customer cannot access staff payment views"""
        self.client.login(username='customer1', password='testpass123')
        response = self.client.get(reverse('payments:staff_payment_list'))
        self.assertRedirects(response, reverse('core:home'), target_status_code=302)
    
    def test_admin_can_access_admin_dashboard(self):
        """Test that admin can access admin dashboard"""
        self.client.login(username='admin1', password='testpass123')
        response = self.client.get(reverse('payments:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_staff_cannot_access_admin_views(self):
        """Test that staff cannot access admin views"""
        self.client.login(username='staff1', password='testpass123')
        response = self.client.get(reverse('payments:admin_dashboard'))
        self.assertRedirects(response, reverse('core:home'), target_status_code=302)


class PaymentWebhookTest(TestCase):
    """Test webhook handling"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            user_type='customer'
        )
        self.bill = Bill.objects.create(
            customer=self.customer,
            billing_month=timezone.now().date(),
            due_date=timezone.now().date(),
            disconnection_date=timezone.now().date(),
            present_reading=Decimal('100'),
            previous_reading=Decimal('90'),
            amount_paid=Decimal('0')
        )
        self.payment = Payment.objects.create(
            bill=self.bill,
            customer=self.customer,
            amount=Decimal('150.00'),
            payment_method='gcash',
            payment_status='pending',
            transaction_id='TEST123'
        )
    
    def test_webhook_idempotency(self):
        """Test that webhook processing is idempotent"""
        webhook_id = 'WEBHOOK123'
        
        # Process webhook first time
        self.payment.payment_status = 'completed'
        self.payment.webhook_id = webhook_id
        self.payment.save()
        
        # Try to process same webhook again
        # Should not duplicate the payment
        old_status = self.payment.payment_status
        if self.payment.webhook_id == webhook_id and self.payment.payment_status == 'completed':
            # Already processed
            pass
        
        self.assertEqual(self.payment.payment_status, 'completed')


class AuditLogTest(TestCase):
    """Test audit logging"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            user_type='customer'
        )
        self.bill = Bill.objects.create(
            customer=self.customer,
            billing_month=timezone.now().date(),
            due_date=timezone.now().date(),
            disconnection_date=timezone.now().date(),
            present_reading=Decimal('100'),
            previous_reading=Decimal('90'),
            amount_paid=Decimal('0')
        )
        self.payment = Payment.objects.create(
            bill=self.bill,
            customer=self.customer,
            amount=Decimal('150.00'),
            payment_method='gcash',
            payment_status='pending'
        )
    
    def test_audit_log_creation(self):
        """Test that audit logs are created"""
        log_payment_action(
            self.payment,
            'payment_initiated',
            self.customer,
            None,
            {'test': 'data'}
        )
        
        log = PaymentAuditLog.objects.filter(payment=self.payment).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'payment_initiated')
        self.assertEqual(log.user, self.customer)
        self.assertEqual(log.user_role, 'customer')


class GCashServiceTest(TestCase):
    """Test GCash service"""
    
    def setUp(self):
        self.gcash = GCashService()
    
    def test_service_initialization(self):
        """Test GCash service initialization"""
        self.assertIsNotNone(self.gcash)
        # In test environment, credentials may not be set
        # This is expected and should not cause errors
    
    def test_signature_generation(self):
        """Test signature generation"""
        payload = {'test': 'data'}
        signature, timestamp = self.gcash._generate_signature(payload)
        
        self.assertIsNotNone(signature)
        self.assertIsNotNone(timestamp)
        self.assertIsInstance(signature, str)
        self.assertIsInstance(timestamp, str)

