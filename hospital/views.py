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
        appointment_time = request.POST.get('appointment_time')
        reason = request.POST.get('reason')

        # Convert time string to time object
        time_obj = datetime.strptime(appointment_time, "%H:%M")

        # Create appointment
        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
        )

        messages.success(request, f'Appointment booked successfully! Your token number is {appointment.token_number}')
        return redirect('appointment_success', appointment_id=appointment.id)

    # GET request - show booking form
    today = timezone.now().date()

    context = {
        'doctor': doctor,
        'today': today,
        'max_date': today + timedelta(days=30),  # Book up to 30 days in advance
    }

    return render(request, 'appointment.html', context)


@login_required
def get_available_time_slots(request, doctor_id):
    """API endpoint to get available time slots"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    date_str = request.GET.get('date')

    if date_str:
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            available_slots = doctor.get_available_time_slots(appointment_date)
            return JsonResponse({'available_slots': available_slots})
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)

    return JsonResponse({'error': 'Date parameter required'}, status=400)


@login_required
def appointment_success(request, appointment_id):
    """Show appointment confirmation page"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)

    context = {
        'appointment': appointment
    }
    return render(request, 'appointment_success.html', context)