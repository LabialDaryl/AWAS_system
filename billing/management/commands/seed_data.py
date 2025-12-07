import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from billing.models import Bill, WaterUpdate
from payments.models import Payment, PaymentProof, PaymentAuditLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with sample data for demo purposes'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database with sample data...')
        
        # Create admin user if not exists
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@awas.com',
                'first_name': 'System',
                'last_name': 'Admin',
                'user_type': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))

        # Create staff users
        staff_data = [
            {'username': 'cashier', 'first_name': 'Maria', 'last_name': 'Santos', 'role': 'cashier'},
            {'username': 'verifier', 'first_name': 'Juan', 'last_name': 'Dela Cruz', 'role': 'verifier'},
            {'username': 'fieldstaff', 'first_name': 'Ana', 'last_name': 'Reyes', 'role': 'field_staff'},
        ]
        
        staff_users = {}
        for staff in staff_data:
            user, created = User.objects.get_or_create(
                username=staff['username'],
                defaults={
                    'email': f"{staff['username']}@awas.com",
                    'first_name': staff['first_name'],
                    'last_name': staff['last_name'],
                    'user_type': 'staff',
                    'is_staff': True,
                }
            )
            if created:
                user.set_password('staff123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created staff user: {user.username}"))
            staff_users[staff['role']] = user

        # Create customers and their bills/payments
        puroks = range(1, 9)  # Purok 1 to 8
        customers_per_purok = 10
        
        # Current date for billing
        today = datetime.now().date()
        billing_month = today.replace(day=1) - timedelta(days=30)  # Previous month
        due_date = billing_month.replace(day=10)  # Due on 10th of the month
        disconnection_date = billing_month.replace(day=25)  # Disconnect after 25th
        
        customer_count = 0
        for purok in puroks:
            for i in range(1, customers_per_purok + 1):
                customer_count += 1
                username = f'purok{purok}user{i}'
                first_name = self._get_random_first_name()
                last_name = self._get_random_last_name()
                
                # Create or get customer
                customer, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f"{username}@example.com",
                        'first_name': first_name,
                        'last_name': last_name,
                        'user_type': 'customer',
                        'purok_number': purok,
                        'specific_address': f'House {i}, Street {chr(64 + i)}',
                        'water_meter_id': f'WM-{purok:02d}-{i:03d}',
                        'is_membership_approved': True,
                    }
                )
                
                if created:
                    customer.set_password('customer123')
                    customer.save()
                    self.stdout.write(self.style.SUCCESS(f'Created customer: {username}'))
                
                # Calculate amounts
                minimum_cubic_meters = 10.0
                rate_per_cubic_meter = 25.0
                minimum_charge = 100.0
                
                # Generate random readings
                previous_reading = random.randint(0, 1000)
                present_reading = previous_reading + random.randint(85, 130)
                consumption = present_reading - previous_reading
                
                # Calculate water charge
                if consumption <= minimum_cubic_meters:
                    water_charge = minimum_charge
                else:
                    excess = consumption - minimum_cubic_meters
                    water_charge = minimum_charge + (excess * rate_per_cubic_meter)
                
                # Check if bill already exists for this customer and month
                bill, created = Bill.objects.get_or_create(
                    customer=customer,
                    billing_month=billing_month,
                    defaults={
                        'due_date': due_date,
                        'disconnection_date': disconnection_date,
                        'previous_reading': previous_reading,
                        'present_reading': present_reading,
                        'water_consumption': consumption,
                        'minimum_cubic_meters': minimum_cubic_meters,
                        'rate_per_cubic_meter': rate_per_cubic_meter,
                        'minimum_charge': minimum_charge,
                        'water_charge': water_charge,
                        'total_amount': water_charge,
                        'amount_paid': 0.0,
                        'balance': water_charge,
                        'payment_status': 'unpaid',
                        'created_by': admin,
                        'is_overdue': False
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created bill for {customer.username} - {billing_month.strftime("%B %Y")}'))
                    
                    # Create payment (with some randomness in status)
                    payment_status = random.choice([
                        'pending', 'processing', 'pending_verification', 
                        'completed', 'completed', 'completed', 'failed', 'cancelled'
                    ])
                    payment_method = random.choice(['gcash', 'walk_in', 'bank_transfer'])
                    
                    # Create payment with only the fields that exist in the model
                    payment = Payment.objects.create(
                        bill=bill,
                        customer=customer,
                        amount=bill.total_amount,
                        payment_method=payment_method,
                        payment_status=payment_status,
                        reference_number=f'REF-{customer.id:04d}-{bill.id:04d}-{random.randint(1000, 9999)}',
                    )
                    
                    # Create payment audit log entry
                    PaymentAuditLog.objects.create(
                        payment=payment,
                        action='payment_created',
                        user=admin,
                        user_role='admin',
                        status=payment_status,
                        details={
                            'method': payment_method,
                            'amount': str(bill.total_amount),
                            'reference': payment.reference_number
                        }
                    )
                    
                    # Create payment proof for non-cash payments
                    if payment_method == 'gcash':
                        proof = PaymentProof.objects.create(
                            customer=customer,
                            bill=bill,
                            reference_number=payment.reference_number,
                            transaction_id=f'GCASH-{random.randint(1000000000, 9999999999)}',
                            screenshot='payment_proofs/sample_receipt.jpg',
                            status='verified' if payment_status == 'completed' else 'pending',
                        )
                        
                        # Create audit log for proof submission
                        PaymentAuditLog.objects.create(
                            payment=payment,
                            action='submitted_proof',
                            user=customer,
                            user_role='customer',
                            status='pending' if payment_status != 'completed' else 'verified',
                            details={
                                'proof_id': str(proof.id),
                                'transaction_id': proof.transaction_id
                            }
                        )
                    
                    # Update bill status based on payment
                    if payment_status == 'completed':
                        bill.payment_status = 'paid'
                        bill.amount_paid = bill.total_amount
                        bill.balance = Decimal('0.00')
                        bill.save()
                        self.stdout.write(self.style.SUCCESS(f'Marked bill as paid for {customer.username}'))
                else:
                    self.stdout.write(self.style.NOTICE(f'Bill already exists for {customer.username} - {billing_month.strftime("%B %Y")}'))
        
        # Create some water updates
        updates = [
            {
                'title': 'Scheduled Maintenance - Purok 1-4',
                'update_type': 'Maintenance',
                'content': 'Water supply will be temporarily interrupted on Friday for maintenance work.',
                'priority': 'high',
                'target_puroks': '1,2,3,4',
                'posted_by': admin,
            },
            {
                'title': 'Water Conservation Notice',
                'update_type': 'Announcements',
                'content': 'Please conserve water during peak hours (6-9 AM, 6-9 PM).',
                'priority': 'medium',
                'target_puroks': '',
                'posted_by': admin,
            },
            {
                'title': 'Emergency Water Interruption',
                'update_type': 'Emergency',
                'content': 'Emergency repair work in progress. Water supply will be restored within 4 hours.',
                'priority': 'urgent',
                'target_puroks': '5,6',
                'posted_by': admin,
            },
        ]
        
        for update_data in updates:
            WaterUpdate.objects.create(**update_data)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded database with {customer_count} customers, their bills, and payments.'))
    
    def _get_random_first_name(self):
        first_names = [
            'Juan', 'Maria', 'Jose', 'Ana', 'Pedro', 'Rosa', 'Antonio', 'Carmen',
            'Manuel', 'Josefa', 'Francisco', 'Teresa', 'Carlos', 'Isabel', 'Jorge',
            'Ramon', 'Rebecca', 'Felipe', 'Luz', 'Roberto', 'Elena', 'Eduardo',
            'Lourdes', 'Alfredo', 'Sofia', 'Rafael', 'Consuelo', 'Ricardo', 'Patricia',
            'Alberto', 'Amparo', 'Arturo', 'Guadalupe', 'Fernando', 'Alicia', 'Javier',
            'Rosario', 'Enrique', 'Beatriz', 'Raul', 'Rosa', 'Oscar', 'Gloria',
            'Gerardo', 'Adriana', 'Raul', 'Aurora', 'Sergio', 'Silvia', 'Ruben', 'Eva'
        ]
        return random.choice(first_names)
    
    def _get_random_last_name(self):
        last_names = [
            'Dela Cruz', 'Reyes', 'Santos', 'Garcia', 'Ramos', 'Mendoza', 'Aquino',
            'Bautista', 'Cruz', 'Del Rosario', 'Domingo', 'Estrada', 'Fernandez',
            'Gonzales', 'Hernandez', 'Ibarra', 'Jimenez', 'Lopez', 'Martinez',
            'Navarro', 'Ocampo', 'Pascual', 'Quizon', 'Rivera', 'Sanchez', 'Torres',
            'Uy', 'Vargas', 'Yap', 'Zamora', 'Alvarez', 'Bautista', 'Cortez',
            'Dela Peña', 'Espinosa', 'Flores', 'Gomez', 'Herrera', 'Ignacio',
            'Jacinto', 'Katigbak', 'Lim', 'Manalo', 'Nolasco', 'Ortega', 'Peralta',
            'Quinto', 'Roxas', 'Salvador', 'Tolentino', 'Umali', 'Valdez', 'Zarate'
        ]
        return random.choice(last_names)
