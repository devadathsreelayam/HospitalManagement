from django.contrib import admin

from hospital.models import Doctor, Patient, User, Appointment


# Register your models here.
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    pass


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_name', 'doctor_name', 'appointment_date', 'appointment_time', 'token_number',
                    'status')
    list_filter = ('status', 'appointment_date', 'doctor')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'doctor__user__first_name')
    date_hierarchy = 'appointment_date'

    def patient_name(self, obj):
        return obj.patient.get_full_name()

    patient_name.short_description = 'Patient'

    def doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"

    doctor_name.short_description = 'Doctor'