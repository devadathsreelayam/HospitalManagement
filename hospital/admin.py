from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe

from hospital.models import Doctor, Patient, User, Appointment, Prescription, LabReport


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Information', {'fields': ('phone', 'user_type', 'profile_image')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Information', {'fields': ('phone', 'user_type', 'profile_image')}),
    )

    list_display = ('username', 'email', 'phone', 'user_type', 'is_staff', 'is_active', 'profile_image_preview')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')

    # Add profile image preview in list view
    def profile_image_preview(self, obj):
        if obj.profile_image:
            return mark_safe(
                f'<img src="{obj.profile_image.url}" style="width: 30px; height: 30px; object-fit: cover; border-radius: 50%;" />')
        return "No Image"

    profile_image_preview.short_description = 'Profile Image'

    # Custom form for better image display in admin
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make the profile image field show a preview in change form
        if obj and obj.profile_image:
            form.base_fields[
                'profile_image'].help_text = f'<img src="{obj.profile_image.url}" style="max-height: 200px; max-width: 200px; border-radius: 5px; margin: 10px 0;" />'
        return form


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
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__user__first_name', 'doctor__user__last_name')

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
    search_fields = ('appointment__patient__first_name', 'appointment__patient__last_name')


@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'appointment', 'doctor', 'report_type', 'uploaded_at')
    list_filter = ('report_type', 'uploaded_at')
    search_fields = ('test_name', 'appointment__patient__first_name', 'appointment__patient__last_name')