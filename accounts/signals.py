from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
try:
    from notifications.signals import notify  # type: ignore
except Exception:  # notifications not installed or incompatible
    notify = None

User = get_user_model()


@receiver(post_save, sender=User)
def user_created_notification(sender, instance, created, **kwargs):
    """Send notification when a new user account is created"""
    if created and instance.is_customer and notify:
        # Notify staff members about new customer
        staff_users = User.objects.filter(user_type='staff')
        for staff in staff_users:
            notify.send(
                instance,
                recipient=staff,
                verb='New customer registered',
                description=f'{instance.get_full_name()} has been registered as a new customer.'
            )
