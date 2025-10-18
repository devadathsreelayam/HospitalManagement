from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('doctors/', views.view_doctors, name='view_doctors'),
    path('doctors/book/<int:doctor_id>/', views.make_appointment, name='make_appointment'),
]