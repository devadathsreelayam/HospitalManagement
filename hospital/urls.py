from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('register', views.register, name='register'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('patient_dashboard', views.patient_dashboard, name='patient_dashboard'),
    path('doctor_dashboard', views.doctor_dashboard, name='doctor_dashboard'),
    path('admin_dashboard', views.admin_dashboard, name='admin_dashboard'),
    path('doctors/', views.view_doctors, name='view_doctors'),
    path('doctors/book/<int:doctor_id>/', views.make_appointment, name='make_appointment'),
    path('booking/success/<int:appointment_id>/', views.appointment_success, name='appointment_success'),
    path('appointments/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
]