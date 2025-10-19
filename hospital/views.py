from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from hospital.models import Doctor
from .forms import PatientRegistrationForm


# Create your views here.
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

    return render(request, 'patient_dash.html', {'user': request.user})


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


def make_appointment(request, doctor_id):
    doctor = Doctor.objects.get(pk=doctor_id)
    context = {
        'doctor': doctor
    }
    return render(request, 'appointment.html', context)