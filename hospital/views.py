from datetime import datetime, timedelta
from django.utils import timezone

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from hospital.models import Doctor, Appointment
from .forms import PatientRegistrationForm


def index(request):
    return render(request, 'home.html')


def login_view(request):
    if request.user.is_authenticated:
        return HttpResponse("Login Successfully")

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name()}!")

            # Redirect based on user type
            if user.user_type == 'patient':
                print('Patient logged in')
                return redirect('patient_dashboard')
            elif user.user_type == 'doctor':
                print('Doctor logged in')
                return redirect('doctor_dashboard')
            else:
                return redirect('admin_dashboard')
        else:
            messages.error(request, f"Invalid Credentials!")
            # return redirect('login')
    return render(request, 'login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, f"You have been logged out successfully")
    return redirect('index')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Registration successful! Welcome {user.get_full_name()}!")
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PatientRegistrationForm()

    return render(request, 'register.html', {'form': form})


@login_required
def dashboard(request):
    if request.user.is_authenticated:
        if request.user.user_type == 'patient':
            return redirect('patient_dashboard')
        elif request.user.user_type == 'doctor':
            return redirect('doctor_dashboard')
        else:
            return redirect('admin_dashboard')

    return redirect('login')

@login_required
def patient_dashboard(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get patient's appointments
    from .models import Appointment
    appointments = Appointment.objects.filter(patient=request.user).order_by('-appointment_date')

    context = {
        'appointments': appointments,
        'patient': request.user.patient  # Access patient profile
    }

    return render(request, 'patient_dash.html', context)


@login_required
def doctor_dashboard(request):
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    return render(request, 'doctor_dash.html', {'user': request.user})


@login_required
def admin_dashboard(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    return render(request, 'admin_dash.html', {'user': request.user})


def view_doctors(request):
    doctors = Doctor.objects.all().select_related('user')

    # Get filter parameters
    specialization = request.GET.get('specialization', '')
    search_query = request.GET.get('search', '')

    # Apply filters
    if specialization:
        doctors = doctors.filter(specialization=specialization)

    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(specialization__icontains=search_query)
        )

    # FIX: Always order by specialization for proper grouping
    doctors = doctors.order_by('specialization')

    # Get specializations for filter dropdown
    specializations = Doctor.SPECIALIZATION_CHOICES

    context = {
        'doctors': doctors,
        'specializations': specializations,
        'selected_specialization': specialization,
        'search_query': search_query,
    }
    return render(request, 'doctors.html', context)


@login_required
def make_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    if request.method == 'POST':
        appointment_date = request.POST.get('appointment_date')
        reason = request.POST.get('reason', '')

        # Basic validation
        if not appointment_date:
            messages.error(request, 'Please select a date.')
            return redirect('make_appointment', doctor_id=doctor_id)

        # Convert string to date object
        try:
            appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('make_appointment', doctor_id=doctor_id)

        today = timezone.now().date()

        # Check if the selected date is valid (not in past)
        if appointment_date_obj < today:
            messages.error(request, 'Cannot book appointments in the past.')
            return redirect('make_appointment', doctor_id=doctor_id)

        # Check if doctor is available on that day
        day_name = appointment_date_obj.strftime('%A').lower()
        available_days = [day.strip().lower() for day in doctor.available_days.split(',')]

        if day_name not in available_days:
            messages.error(request,
                           f'Doctor is not available on {appointment_date_obj.strftime("%A")}. Available days: {doctor.available_days.title()}')
            return redirect('make_appointment', doctor_id=doctor_id)

        # Check if patient already has an appointment with this doctor on same date
        existing_appointment = Appointment.objects.filter(
            patient=request.user,
            doctor=doctor,
            appointment_date=appointment_date_obj,
            status='scheduled'
        ).exists()

        if existing_appointment:
            messages.error(request, 'You already have an appointment with this doctor on the selected date.')
            return redirect('make_appointment', doctor_id=doctor_id)

        # Create appointment
        try:
            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                appointment_date=appointment_date_obj,
                reason=reason
            )

            messages.success(request,
                             f'Appointment booked successfully! Your token number is {appointment.token_number}')
            return redirect('appointment_success', appointment_id=appointment.id)

        except Exception as e:
            messages.error(request, f'Error booking appointment. Please try again.')
            print(f"Appointment creation error: {e}")  # For debugging
            return redirect('make_appointment', doctor_id=doctor_id)

    # GET request - show booking form
    today = timezone.now().date()

    # Calculate today's appointments for this doctor
    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today,
        status='scheduled'
    )

    last_token = today_appointments.last().token_number if today_appointments.exists() else 0

    context = {
        'doctor': doctor,
        'today': today,
        'max_date': today + timedelta(days=30),
        'today_appointments_count': today_appointments.count(),
        'last_token_today': last_token,
    }
    return render(request, 'appointment.html', context)


@login_required
def appointment_success(request, appointment_id):
    """Show appointment confirmation page"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)

    context = {
        'appointment': appointment
    }
    return render(request, 'appointment_success.html', context)