from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class User(AbstractUser):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
    )

    # Don't define user_id - AbstractUser already has 'id'
    # Don't define full_name - use first_name and last_name from AbstractUser
    phone = models.CharField(max_length=10, blank=True)  # Increased length
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='patient')

    def __str__(self):
        return f"{self.username} ({self.user_type})"


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    address = models.TextField()
    emergency_contact = models.CharField(max_length=10)

    def __str__(self):
        return f"#{self.user_id} {self.user.get_full_name()}"


class Doctor(models.Model):
    SPECIALIZATION_CHOICES = [
        ('cardiology', 'Cardiology'),
        ('dermatology', 'Dermatology'),
        ('pediatrics', 'Pediatrics'),
        ('orthopedics', 'Orthopedics'),
        ('neurology', 'Neurology'),
        ('gynecology', 'Gynecology'),
        ('psychiatry', 'Psychiatry'),
        ('dentistry', 'Dentistry'),
        ('general', 'General Medicine'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100, choices=SPECIALIZATION_CHOICES, default='general')
    start_time = models.TimeField(default='09:00:00')
    end_time = models.TimeField(default='17:00:00')
    available_days = models.CharField(max_length=100)  # monday, tuesday, ...
    max_appointments = models.IntegerField(default=50)

    def get_available_days_list(self):
        """Convert comma-separated string to list"""
        return self.available_days.split(',') if self.available_days else []

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"