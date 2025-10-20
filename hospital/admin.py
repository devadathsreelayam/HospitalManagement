from django.contrib import admin

from hospital.models import Doctor, Patient, User, Appointment, Prescription, LabReport


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
    list_display = ('id', 'get_patient_name', 'get_doctor_name', 'appointment_date', 'token_number', 'estimated_time',
                    'status')
    list_filter = ('status', 'appointment_date', 'doctor')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'doctor__user__first_name')

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

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