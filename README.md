# AWAS - Barangay Water Billing and Management System

A comprehensive Django-based web application for managing water billing, payments, and customer management for barangays with multiple puroks.

## Features

### Landing Page (Public)
- Water connection request form
- System information
- Contact details

### Customer Dashboard (Registered Members)
- View monthly water bills and consumption
- Make online payments (GCash, PayPal, PayMaya)
- View payment history
- Manage profile
- Search other registered users
- Post complaints/suggestions
- Receive notifications for due dates

### Staff Dashboard
- Create monthly bills for customers
- Monitor customer status (paid/unpaid, active/inactive)
- Manage customer accounts (suspend/reinstate)
- View payment records
- Post water updates/announcements
- Review and approve membership requests

### Admin Panel (Django Built-in)
- Add multiple staff accounts
- Full system management
- Approve membership requests

## Technology Stack

- **Backend**: Python 3.x, Django 4.x
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Database**: SQLite (development) / PostgreSQL (production)
- **Payment Integration**: GCash, PayPal, PayMaya APIs

## Project Structure

```
awas/
├── manage.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── awas_project/          # Main project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/              # User authentication & profiles
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── signals.py
├── billing/               # Water billing management
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── payments/              # Payment processing
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── notifications/         # Notification system
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── complaints/            # Customer complaints & suggestions
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── core/                  # Landing page & general views
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── water-theme.css
│   ├── js/
│   │   └── main.js
│   └── images/
│       └── logo.png
├── templates/
│   ├── base.html
│   ├── landing/
│   │   ├── index.html
│   │   └── connection_request.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── profile.html
│   │   └── user_search.html
│   ├── customer/
│   │   ├── dashboard.html
│   │   ├── bills.html
│   │   ├── payment.html
│   │   └── payment_history.html
│   ├── staff/
│   │   ├── dashboard.html
│   │   ├── create_bill.html
│   │   ├── customer_list.html
│   │   ├── customer_detail.html
│   │   ├── membership_requests.html
│   │   └── water_updates.html
│   ├── complaints/
│   │   ├── list.html
│   │   └── create.html
│   └── notifications/
│       └── list.html
└── media/
    └── uploads/
```

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd awas
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create superuser
```bash
python manage.py createsuperuser
```

7. Run development server
```bash
python manage.py runserver
```

8. Access the application at `http://localhost:8000`

## Configuration

### Purok Numbers
The system supports 8 puroks (1-8). Configure in `settings.py`:
```python
PUROK_CHOICES = [(i, f'Purok {i}') for i in range(1, 9)]
```

### Payment Gateways
Configure API keys in `.env`:
```
GCASH_API_KEY=your_gcash_key
PAYPAL_CLIENT_ID=your_paypal_id
PAYMAYA_PUBLIC_KEY=your_paymaya_key
```

## User Roles

1. **Admin**: Full system access via Django admin panel
2. **Staff**: Manage bills, customers, and payments
3. **Customer**: View bills, make payments, post complaints
4. **Visitor**: View landing page, request water connection

## License

Proprietary - Barangay Water Management System

## Support

For issues and questions, contact the system administrator.
