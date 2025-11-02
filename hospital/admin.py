from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hospital.models import Doctor, Patient, User, Appointment, Prescription, LabReport


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Information', {'fields': ('phone', 'user_type')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Information', {'fields': ('phone', 'user_type')}),
    )

    list_display = ('username', 'email', 'phone', 'user_type', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization')
    list_filter = ('specialization',)
    search_fields = ('user__first_name', 'user__last_name', 'specialization')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'gender')
    list_filter = ('gender', )
    search_fields = ('user__first_name', 'user__last_name')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_patient_name', 'get_doctor_name', 'appointment_date', 'token_number', 'estimated_time',
                    'status')
    list_filter = ('status', 'appointment_date', 'doctor')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'doctor__user__first_name')

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()

    get_patient_name.short_description = 'Patient'

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"

    get_doctor_name.short_description = 'Doctor'


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('appointment__patient__user__first_name', 'appointment__patient__user__last_name')


@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'appointment', 'doctor', 'report_type', 'uploaded_at')
    list_filter = ('report_type', 'uploaded_at')
    search_fields = ('test_name', 'appointment__patient__user__first_name')