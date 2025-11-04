from django.conf.urls.static import static
from django.conf import settings
from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patient_dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('doctor_dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('doctors/', views.view_doctors, name='view_doctors'),
    path('doctors/book/<int:doctor_id>/', views.make_appointment, name='make_appointment'),
    path('booking/success/<int:appointment_id>/', views.appointment_success, name='appointment_success'),
    path('appointment/<int:appointment_id>/download-token/', views.download_appointment_token, name='download_appointment_token'),
    path('appointments/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('appointments/complete/<int:appointment_id>/', views.complete_appointment, name='complete_appointment'),
    path('appointments/revert/<int:appointment_id>/', views.revert_appointment, name='revert_appointment'),
    path('prescriptions/add/', views.add_prescription, name='add_prescription'),
    path('prescriptions/<int:appointment_id>/', views.get_prescription, name='get_prescription'),
    path('patient_history/<int:patient_id>', views.patient_history, name='patient_history'),
    path('patient/medical-history/', views.patient_treatment_history, name='patient_treatment_history'),
    path('patient/medical-history/doctor/<int:doctor_id>/', views.patient_doctor_history, name='patient_doctor_history'),
    path('lab-report/upload/<int:patient_id>/', views.upload_lab_report, name='upload_lab_report'),
    path('lab-report/delete/<int:report_id>/', views.delete_lab_report, name='delete_lab_report'),
    path('patient/lab-reports/', views.patient_lab_reports, name='patient_lab_reports'),
    path('patient/profile/update/', views.patient_profile_update, name='patient_profile_update'),
    path('admin/doctors/', views.admin_doctors_list, name='admin_doctors_list'),
    path('admin/doctors/create/', views.admin_doctor_create, name='admin_doctor_create'),
    path('admin/doctors/<int:doctor_id>/', views.admin_doctor_detail, name='admin_doctor_detail'),
    path('admin/doctors/<int:doctor_id>/edit/', views.admin_doctor_edit, name='admin_doctor_edit'),
    path('admin/doctors/<int:doctor_id>/toggle-active/', views.admin_doctor_toggle_active, name='admin_doctor_toggle_active'),
    path('admin/patients/', views.admin_patients_list, name='admin_patients_list'),
    path('admin/patients/<int:patient_id>/', views.admin_patient_detail, name='admin_patient_detail'),
    path('admin/patients/<int:patient_id>/toggle-active/', views.admin_patient_toggle_active, name='admin_patient_toggle_active'),

    # Admin Appointments
    path('admin/appointments/', views.admin_appointments_list, name='admin_appointments_list'),
    path('admin/appointments/analytics/', views.admin_appointments_analytics, name='admin_appointments_analytics'),

    # Admin Lab Reports
    path('admin/lab-reports/', views.admin_lab_reports_list, name='admin_lab_reports_list'),
    path('admin/lab-reports/statistics/', views.admin_lab_reports_statistics, name='admin_lab_reports_statistics'),


    path('patient/profile/settings/', views.patient_profile_settings, name='patient_profile_settings'),
    path('patient/profile/image/update/', views.patient_profile_image_update, name='patient_profile_image_update'),
    path('patient/password/change/', views.patient_password_change, name='patient_password_change'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)