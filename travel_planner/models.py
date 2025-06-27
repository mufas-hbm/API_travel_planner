from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings # reference AUTH_USER_MODEL

# Create your models here.
class CustomUser(AbstractUser):
    TRAVEL_STYLE_CHOICES = [
        ('ADVENTURE', 'Adventure'),
        ('RELAXATION', 'Relaxation'),
        ('CULTURAL', 'Cultural'),
        ('LUXURY', 'Luxury'),
        ('FAMILY', 'Family-friendly'),
        ('CRUISE', 'Cruise'),
        ('ECOTOURISM', 'Ecotourism'),
        ('BUSINESS', 'Business Travel'),
    ]
    date_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    preferred_travel_style = models.CharField(max_length=150,blank=True, null=True, choices=TRAVEL_STYLE_CHOICES)

    def __str__(self):
        return self.username
    
class Destination(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    is_popular = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['name']
        unique_together = ('name','city', 'country')
    
    def __str__(self):
        return f'{self.name}, {self.country}'

class TravelPlan(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    destinations = models.ManyToManyField(
        'Destination',
        through='TravelPlanDestination',
        related_name='travel_plans'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    is_public = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}, from {self.start_date} until {self.end_date}'

class TravelPlanDestination(models.Model):
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0) # define the sequence of destinations
    arrival_date = models.DateField(null=True, blank=True)
    departure_date = models.DateField(null=True, blank=True)

    class Meta:
        # Ensures a destination can only appear once per travel plan entry
        unique_together = ('travel_plan', 'destination')
        ordering = ['order']

    def __str__(self):
        return f"{self.destination.name} in {self.travel_plan.name}"

class Activity(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.SET_NULL, null=True)
    destination = models.ForeignKey(Destination, on_delete=models.SET_NULL, null=True, related_name='activities')
    date = models.DateTimeField()
    cost = models.DecimalField(max_digits=6, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.name}, cost: {self.cost:.2f}'

class Comment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Generic Foreign Key Fields ---
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField() 
    content_object = GenericForeignKey('content_type', 'object_id')
    # ----------------------------------

    class Meta:
        ordering = ['-created_at'] # Newest comments first

    def __str__(self):
        return f'Comment by {self.user.username} on {self.content_object.__class__.__name__}: {self.content_object}'

    