"""
Signals to automatically provision CustomerProfile or RiderProfile when a User is created or updated.
Owned by Developer 1.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomerProfile, RiderProfile, User, UserRole


@receiver(post_save, sender=User)
def ensure_role_profile(sender, instance: User, created: bool, **kwargs):
    """
    Automatically create CustomerProfile for CUSTOMER users and RiderProfile for RIDER users.
    """
    if instance.role == UserRole.CUSTOMER:
        CustomerProfile.objects.get_or_create(user=instance)
    elif instance.role == UserRole.RIDER:
        RiderProfile.objects.get_or_create(user=instance)
