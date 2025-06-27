from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Avg

class User(AbstractUser):
    ROLE_CHOICES = [
        ("chef", "Chef"),
        ("customer", "Customer"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)  
    email = models.EmailField(unique=True, blank=False, null=False)


    def __str__(self):
        return self.username

def chef_picture_upload_path(instance, filename):
    
    return f"chef_profiles/{instance.user.id}/profile_picture.{filename.split('.')[-1]}"

    
GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
]

class ChefProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to=chef_picture_upload_path, blank=True, null=True, default="defaults/default_profile.png")
    experience = models.IntegerField(null=True, blank=True)  
    specialties = models.CharField(max_length=255, blank=True, null=True) 
    location = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    contact_number = models.CharField(max_length=11, null=True, blank=True)

    # Availability fields
    is_available = models.BooleanField(default=True)  # Global availability
    breakfast_available = models.BooleanField(default=True)
    lunch_available = models.BooleanField(default=True)
    dinner_available = models.BooleanField(default=True)
    urgent_booking_available = models.BooleanField(default=True)
    pre_booking_available = models.BooleanField(default=True)

    # Rating fields
    average_rating = models.FloatField(default=0) 
    total_ratings = models.IntegerField(default=0)  

    def update_rating(self):
        # Update the average rating and total ratings after each rating submission
        ratings = ChefRating.objects.filter(chef=self.user)
        total_ratings = ratings.count()
        if total_ratings > 0:
            avg_rating = ratings.aggregate(Avg('rating'))['rating__avg']
            self.average_rating = avg_rating
        else:
            self.average_rating = 0
        self.total_ratings = total_ratings
        self.save()

    def __str__(self):
        return self.full_name if self.full_name else self.user.username
    
    def update_availability(self):
        # Automatically disable individual meal slots, urgent booking, and pre-booking if is_available is False
        if not self.is_available:
            self.breakfast_available = False
            self.lunch_available = False
            self.dinner_available = False
            self.urgent_booking_available = False
            self.pre_booking_available = False
        elif self.is_available:
            self.breakfast_available = True
            self.lunch_available = True
            self.dinner_available = True
            self.urgent_booking_available = True
            self.pre_booking_available = True
        self.save()


class Dish(models.Model):
    AVAILABLE_TIMES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ]

    AVAILABLE_TIME_RANGES = {
        'breakfast': ('08:00', '10:00'),
        'lunch': ('12:00', '14:00'),
        'dinner': ('18:00', '20:00'),
    }

    chef = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='dishes',
        limit_choices_to={'role': 'chef'} 
    )
    name = models.CharField(max_length=255)
    picture = models.ImageField(upload_to='dish_pictures/',  default="defaults/default_dish.png")
    description = models.TextField()
    available_time = models.CharField(max_length=20, choices=AVAILABLE_TIMES)
    serving_number = models.PositiveIntegerField()
    price = models.PositiveIntegerField()  
    time_range_start = models.TimeField(null=True, blank=True)  # Start time of the slot
    time_range_end = models.TimeField(null=True, blank=True)  # End time of the slot

    def save(self, *args, **kwargs):
        # Automatically set time range based on the available_time (meal type)
        if not self.time_range_start and not self.time_range_end:  # Only set if not already set
            time_range = self.AVAILABLE_TIME_RANGES.get(self.available_time)
            if time_range:
                self.time_range_start = time_range[0]
                self.time_range_end = time_range[1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} by Chef {self.chef.username}"


class Booking(models.Model):
    SLOT_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ]

    BOOKING_TYPE_CHOICES = [
        ('urgent', 'Urgent'),
        ('prebooking', 'Pre-booking'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_bookings')
    chef = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chef_bookings')
    dishes = models.ManyToManyField(Dish, related_name="bookings")  
    slot = models.CharField(max_length=10, choices=SLOT_CHOICES)
    booking_type = models.CharField(max_length=12, choices=BOOKING_TYPE_CHOICES)
    date = models.DateField()
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    special_instructions = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_updated_at = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.customer.username} at {self.slot} on {self.date}"



class ChefRating(models.Model):
    chef = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chef_ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="given_chef_ratings")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('chef', 'user')  # Prevent duplicate ratings
