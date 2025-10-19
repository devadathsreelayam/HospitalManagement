from django.contrib.auth.models import AbstractUser
from django.db import models


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

    def get_available_time_slots(self, date):
        """Get available timeslots for given date"""
        from .utils import generate_time_slots

        # Generate all possible slots
        all_slots = generate_time_slots(self.start_time, self.end_time)

        # Get booked appointments for that date
        booked_appointments = Appointment.objects.filter(
            doctor=self,
            appointment_date=date,
            status='scheduled'
        )

        # Get booked time slots
        booked_slots = [app.appointment_time.strftime("%H:%M") for app in booked_appointments]

        # Return available slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        return available_slots

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}, {self.qualification} - {self.specialization.capitalize()}"


class Appointment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'patient'})
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    token_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=(
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ), default='scheduled')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-generate token number if not set
        if not self.token_number:
            # Count appointments for same doctor, date, and time slot
            same_slot_appointments = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                appointment_time=self.appointment_time,
                status='scheduled'
            )
            self.token_number = same_slot_appointments.count() + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token #{self.token_number} - {self.patient.username} with Dr. {self.doctor.user.last_name}"