from django.contrib.auth.models import AbstractUser
from django.db import models

from datetime import datetime, timedelta


# Create your models here.
class User(AbstractUser):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
    )

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
    qualification = models.CharField(max_length=20, default='MBBS')
    specialization = models.CharField(max_length=100, choices=SPECIALIZATION_CHOICES, default='general')
    start_time = models.TimeField(default='09:00:00')
    end_time = models.TimeField(default='17:00:00')
    available_days = models.CharField(max_length=100)  # monday, tuesday, ...
    max_appointments = models.IntegerField(default=50)

    def get_available_days_list(self):
        """Convert comma-separated string to list"""
        return self.available_days.split(',') if self.available_days else []

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}, {self.qualification} - {self.specialization.capitalize()}"


class Appointment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'patient'})
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment_date = models.DateField()
    token_number = models.IntegerField(default=0)
    estimated_time = models.TimeField()  # Store calculated time
    status = models.CharField(max_length=20, choices=(
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ), default='scheduled')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token_number or self.token_number == 0:
            # Get the last token number for this doctor on this date
            last_appointment = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                status='scheduled'
            ).order_by('-token_number').first()

            if last_appointment:
                self.token_number = last_appointment.token_number + 1
            else:
                self.token_number = 1  # First appointment of the day

        # Calculate and store estimated time
        if not self.estimated_time:
            self.estimated_time = self.calculate_estimated_time()

        super().save(*args, **kwargs)

    def calculate_estimated_time(self):
        """Calculate estimated time based on token number (10 minutes per patient)"""
        if self.token_number == 1:
            return self.doctor.start_time
        else:
            # Start time + (token_number - 1) * 10 minutes
            start_datetime = datetime.combine(self.appointment_date, self.doctor.start_time)
            estimated_datetime = start_datetime + timedelta(minutes=(self.token_number - 1) * 10)
            return estimated_datetime.time()

    def __str__(self):
        return f"Token #{self.token_number} - {self.patient.username} at {self.estimated_time.strftime('%H:%M')}"

    class Meta:
        ordering = ['appointment_date', 'doctor', 'token_number']
