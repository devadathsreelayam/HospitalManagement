from django.db.models import Q
from django.shortcuts import render

from hospital.models import Doctor


# Create your views here.
def index(request):
    return render(request, 'home.html')


def login(request):
    render(request, 'login.html')


def register(request):
    render(request, 'register.html')


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