from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import ChefProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_chef_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a ChefProfile when a new chef user registers.
    """
    if created and instance.role == 'chef':  # Check if user is a chef
        ChefProfile.objects.create(user=instance)
