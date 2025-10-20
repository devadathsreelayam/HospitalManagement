from datetime import datetime, timedelta
from django.utils import timezone

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from hospital.models import Doctor, Appointment, Prescription, User, Patient, LabReport
from .forms import PatientRegistrationForm, LabReportForm


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
    appointments = Appointment.objects.filter(patient=request.user).order_by('-appointment_date', 'token_number')

    # Calculate counts
    total_appointments = appointments.count()
    scheduled_appointments = appointments.filter(status='scheduled').count()
    completed_appointments = appointments.filter(status='completed').count()

    context = {
        'appointments': appointments,
        'today': timezone.now().date(),
        'total_appointments': total_appointments,
        'scheduled_appointments': scheduled_appointments,
        'completed_appointments': completed_appointments,
    }

    return render(request, 'patient_dash.html', context)


@login_required
def doctor_dashboard(request):
    """Doctor dashboard with appointment management"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get the doctor instance
    try:
        doctor = request.user.doctor
    except Doctor.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('dashboard')

    # Get selected date from request or default to today
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # OPTIMIZED: Prefetch prescriptions to avoid N+1 queries
    appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=selected_date
    ).select_related('patient', 'doctor').prefetch_related('prescription').order_by('token_number')

    # Calculate statistics
    today = timezone.now().date()

    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today
    )

    today_appointments_count = today_appointments.filter(status='scheduled').count()
    completed_today_count = today_appointments.filter(status='completed').count()

    context = {
        'doctor': doctor,
        'appointments': appointments,
        'selected_date': selected_date,
        'today': today,
        'today_appointments_count': today_appointments_count,
        'completed_today_count': completed_today_count,
        'min_date': timezone.now().date() - timedelta(days=30),
        'max_date': timezone.now().date() + timedelta(days=30),
    }
    return render(request, 'doctor_dash.html', context)


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


@login_required
def cancel_appointment(request, appointment_id):
    """Cancel an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)

    if request.method == 'POST':
        if appointment.cancel():
            messages.success(request, 'Appointment cancelled successfully!')
        else:
            messages.error(request,
                           'Cannot cancel this appointment. It may be too close to the appointment time or already completed/cancelled.')

        return redirect('patient_dashboard')

    # If someone tries to access via GET, redirect to dashboard
    return redirect('patient_dashboard')


@login_required
def add_prescription(request):
    """Add or edit prescription for an appointment - HANDLES BOTH GET AND POST"""
    print("🟢 add_prescription view called")  # Debug

    if request.user.user_type != 'doctor':
        print("Access denied - not a doctor")  # Debug
        return JsonResponse({'success': False, 'error': 'Access denied'})

    if request.method == 'POST':
        print("🟢 POST request received")  # Debug

        try:
            # Get data from POST request
            appointment_id = request.POST.get('appointment_id')
            prescription_text = request.POST.get('prescription_text', '').strip()

            print(f"📋 Appointment ID: {appointment_id}")  # Debug
            print(f"📋 Prescription text length: {len(prescription_text)}")  # Debug

            if not appointment_id:
                print("No appointment ID")  # Debug
                return JsonResponse({'success': False, 'error': 'Appointment ID required'})

            # Get appointment
            try:
                appointment = Appointment.objects.get(id=appointment_id, doctor=request.user.doctor)
                print(f"Found appointment: {appointment}")  # Debug
            except Appointment.DoesNotExist:
                print("Appointment not found")  # Debug
                return JsonResponse({'success': False, 'error': 'Appointment not found'})

            # Check if prescription is allowed
            if not appointment.can_prescribe():
                print("Cannot prescribe for future appointment")  # Debug
                return JsonResponse({'success': False, 'error': 'Cannot prescribe for future appointments'})

            if not prescription_text:
                print("Empty prescription text")  # Debug
                return JsonResponse({'success': False, 'error': 'Prescription text is required'})

            # Create or update prescription
            try:
                prescription = Prescription.objects.get(appointment=appointment)
                print("🟡 Updating existing prescription")  # Debug
                prescription.prescription_text = prescription_text
                prescription.save()
                created = False
            except Prescription.DoesNotExist:
                print("🟡 Creating new prescription")  # Debug
                prescription = Prescription.objects.create(
                    appointment=appointment,
                    prescription_text=prescription_text
                )
                created = True

            print("Prescription saved successfully")  # Debug
            return JsonResponse({
                'success': True,
                'message': 'Prescription saved successfully',
                'created': created
            })

        except Exception as e:
            print(f"Exception in view: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()  # This will print full traceback to console
            return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})

    else:
        # GET request - should not happen for this endpoint
        print("GET request to POST-only endpoint")  # Debug
        return JsonResponse({'success': False, 'error': 'Method not allowed'})


@login_required
def get_prescription(request, appointment_id):
    """Get prescription for an appointment - Allow both doctor and patient"""
    print(f"🟢 get_prescription called for appointment {appointment_id} by {request.user.user_type}")

    try:
        # Doctors can view prescriptions for their appointments
        if request.user.user_type == 'doctor':
            appointment = Appointment.objects.get(id=appointment_id, doctor=request.user.doctor)
            print(f"Doctor accessing prescription for their appointment")

        # Patients can view their own prescriptions
        elif request.user.user_type == 'patient':
            appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
            print(f"Patient accessing their own prescription")

        else:
            print("Access denied - invalid user type")
            return JsonResponse({'error': 'Access denied'}, status=403)

        print(f"Found appointment: {appointment}")

        # SAFELY check if prescription exists
        try:
            prescription = Prescription.objects.get(appointment=appointment)
            print(f"Found prescription: {prescription.prescription_text[:50]}...")
            return JsonResponse({'prescription_text': prescription.prescription_text})

        except Prescription.DoesNotExist:
            print("🟡 No prescription found for this appointment")
            return JsonResponse({'prescription_text': ''})

    except Appointment.DoesNotExist:
        print(f"Appointment {appointment_id} not found or access denied for user {request.user}")
        return JsonResponse({'error': 'Appointment not found or access denied'}, status=404)

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Server error'}, status=500)


@login_required
def complete_appointment(request, appointment_id):
    """Mark appointment as completed"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('doctor_dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor)

    if appointment.complete_appointment():
        messages.success(request, 'Appointment marked as completed.')
    else:
        messages.error(request, 'Could not complete appointment.')

    return redirect('doctor_dashboard')


@login_required
def revert_appointment(request, appointment_id):
    """Revert completed appointment back to scheduled"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('doctor_dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor)

    if appointment.status == 'completed':
        appointment.status = 'scheduled'
        appointment.save()
        messages.success(request, 'Appointment reverted to scheduled status.')
    else:
        messages.error(request, 'Can only revert completed appointments.')

    return redirect('doctor_dashboard')


@login_required
def patient_appointment_history(request, patient_id=None, doctor_id=None):
    """
    Unified view for patient history
    - For doctors: view patient's history with them
    - For patients: view their own history with specific doctor or all doctors
    """
    context = {}

    if request.user.user_type == 'doctor':
        # Doctor viewing patient's history
        if not patient_id:
            messages.error(request, 'Patient ID required.')
            return redirect('doctor_dashboard')

        try:
            patient_user = User.objects.get(id=patient_id, user_type='patient')
            patient_profile = patient_user.patient

            # Get appointments between this patient and current doctor
            appointments = Appointment.objects.filter(
                patient=patient_user,
                doctor=request.user.doctor
            ).select_related('prescription').order_by('-appointment_date', '-created_at')

            context.update({
                'view_type': 'doctor_view',
                'patient_user': patient_user,
                'patient_profile': patient_profile,
                'viewing_doctor': request.user.doctor,
            })

        except (User.DoesNotExist, Patient.DoesNotExist):
            messages.error(request, 'Patient not found.')
            return redirect('doctor_dashboard')

    elif request.user.user_type == 'patient':
        # Patient viewing their own history
        if doctor_id:
            # View history with specific doctor
            try:
                doctor = Doctor.objects.get(id=doctor_id)
                appointments = Appointment.objects.filter(
                    patient=request.user,
                    doctor=doctor
                ).select_related('prescription').order_by('-appointment_date', '-created_at')

                context.update({
                    'view_type': 'patient_doctor_view',
                    'viewing_doctor': doctor,
                })

            except Doctor.DoesNotExist:
                messages.error(request, 'Doctor not found.')
                return redirect('patient_dashboard')
        else:
            # View all history across all doctors
            appointments = Appointment.objects.filter(
                patient=request.user
            ).select_related('doctor', 'prescription', 'doctor__user').order_by('-appointment_date', '-created_at')

            context.update({
                'view_type': 'patient_all_view',
            })
    else:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    context['appointments'] = appointments
    return render(request, 'patient_history.html', context)


@login_required
def patient_history(request, patient_id):
    """View patient's appointment history and prescriptions"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('doctor_dashboard')

    try:
        # Get patient user
        patient_user = User.objects.get(id=patient_id, user_type='patient')
        patient_profile = patient_user.patient

        # Get all appointments for this patient with current doctor
        appointments = Appointment.objects.filter(
            patient=patient_user,
            doctor=request.user.doctor
        ).select_related('prescription').prefetch_related('lab_reports').order_by('-appointment_date', '-created_at')

        # Get ALL lab reports for this patient (combined view)
        lab_reports = LabReport.objects.filter(
            appointment__patient=patient_user,
            doctor=request.user.doctor
        ).select_related('appointment').order_by('-uploaded_at')

        # Calculate lab report statistics
        unique_report_types = lab_reports.values('report_type').distinct().count()
        latest_report = lab_reports.first()
        oldest_report = lab_reports.last()

        # Get return date from URL parameters
        return_date = request.GET.get('return_date', timezone.now().date().strftime('%Y-%m-%d'))

        context = {
            'patient_user': patient_user,
            'patient_profile': patient_profile,
            'appointments': appointments,
            'doctor': request.user.doctor,
            'return_date': return_date,
            'lab_reports': lab_reports,
            'unique_report_types': unique_report_types,
            'latest_report_date': latest_report.uploaded_at if latest_report else None,
            'oldest_report_date': oldest_report.uploaded_at if oldest_report else None,
            'today': timezone.now().date(),
        }
        return render(request, 'patient_history.html', context)

    except User.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('doctor_dashboard')
    except Patient.DoesNotExist:
        messages.error(request, 'Patient profile not found.')
        return redirect('doctor_dashboard')


@login_required
def patient_treatment_history(request):
    """Show summary of all doctors patient has consulted"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('patient_dashboard')

    # Get all distinct doctors the patient has appointments with
    from django.db.models import Count, Max, Min, Exists, OuterRef

    # Subquery to check if any appointment with this doctor has a prescription
    prescription_exists = Prescription.objects.filter(
        appointment__doctor=OuterRef('pk'),
        appointment__patient=request.user
    )

    # Get doctors with statistics
    doctors = Doctor.objects.filter(
        appointment__patient=request.user
    ).distinct().annotate(
        total_consultations=Count('appointment'),
        last_visit=Max('appointment__appointment_date'),
        first_visit=Min('appointment__appointment_date'),
        has_prescriptions=Exists(prescription_exists)
    ).select_related('user')

    # Calculate overall statistics
    appointments = Appointment.objects.filter(patient=request.user)
    total_consultations = appointments.count()
    total_doctors = doctors.count()

    if appointments.exists():
        first_visit_overall = appointments.earliest('appointment_date').appointment_date
        last_visit_overall = appointments.latest('appointment_date').appointment_date
    else:
        first_visit_overall = None
        last_visit_overall = None

    context = {
        'doctors_history': doctors,  # Now using the annotated queryset directly
        'total_consultations': total_consultations,
        'total_doctors': total_doctors,
        'first_visit_overall': first_visit_overall,
        'last_visit_overall': last_visit_overall,
    }

    return render(request, 'patient_treatment_history.html', context)


@login_required
def patient_doctor_history(request, doctor_id):
    """Show detailed history with specific doctor"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('patient_dashboard')

    # Get doctor and verify patient has history with them
    doctor = get_object_or_404(Doctor, id=doctor_id)

    # Get all appointments with this doctor
    appointments = Appointment.objects.filter(
        patient=request.user,
        doctor=doctor
    ).prefetch_related('prescription').order_by('-appointment_date', '-created_at')

    if not appointments.exists():
        messages.error(request, 'No treatment history found with this doctor.')
        return redirect('patient_treatment_history')

    # Check if any appointment has prescriptions (safely)
    has_prescriptions = False
    for appointment in appointments:
        try:
            if hasattr(appointment, 'prescription') and appointment.prescription:
                has_prescriptions = True
                break
        except Prescription.DoesNotExist:
            continue

    has_lab_reports = LabReport.objects.filter(
        appointment__in=appointments
    ).exists()

    # Calculate statistics for this doctor
    total_visits = appointments.count()
    completed_visits = appointments.filter(status='completed').count()
    first_visit = appointments.earliest('appointment_date').appointment_date
    last_visit = appointments.latest('appointment_date').appointment_date

    context = {
        'doctor': doctor,
        'appointments': appointments,
        'total_visits': total_visits,
        'completed_visits': completed_visits,
        'first_visit': first_visit,
        'last_visit': last_visit,
        'has_prescriptions': has_prescriptions,
        'today': timezone.now().date(),  # Add this for template
        'has_lab_reports': has_lab_reports,
    }

    return render(request, 'patient_doctor_history.html', context)


@login_required
def upload_lab_report(request, patient_id):
    """Upload lab report for a patient"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    patient = get_object_or_404(User, id=patient_id, user_type='patient')

    # Get the most recent appointment
    recent_appointment = Appointment.objects.filter(
        patient=patient,
        doctor=request.user.doctor
    ).order_by('-appointment_date').first()

    if request.method == 'POST':
        form = LabReportForm(request.POST, request.FILES)
        if form.is_valid():
            lab_report = form.save(commit=False)
            lab_report.appointment = recent_appointment
            lab_report.doctor = request.user.doctor
            lab_report.save()

            messages.success(request, f'Lab report "{lab_report.test_name}" uploaded successfully!')
            # FIX: Add patient_id argument to the redirect
            return redirect('patient_history', patient_id=patient_id)
    else:
        form = LabReportForm()

    context = {
        'form': form,
        'patient': patient,
        'recent_appointment': recent_appointment,
    }
    return render(request, 'upload_lab_report.html', context)


@login_required
def delete_lab_report(request, report_id):
    """Delete a lab report"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    lab_report = get_object_or_404(LabReport, id=report_id, doctor=request.user.doctor)

    if request.method == 'POST':
        patient_id = lab_report.appointment.patient.id  # Get patient_id from the lab report
        lab_report.delete()
        messages.success(request, 'Lab report deleted successfully!')
        # FIX: Add patient_id argument
        return redirect('patient_history', patient_id=patient_id)

    return redirect('doctor_dashboard')