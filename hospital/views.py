from datetime import datetime, timedelta
from django.utils import timezone

from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from hospital.models import Doctor, Appointment, Prescription, User, Patient, LabReport
from .forms import PatientRegistrationForm, LabReportForm, PatientProfileUpdateForm, DoctorUserForm, DoctorProfileForm


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

    # Calculate statistics
    total_doctors = Doctor.objects.count()
    total_patients = Patient.objects.count()
    total_users = User.objects.count()

    # Appointment statistics
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(appointment_date=today)
    total_appointments_today = today_appointments.count()
    completed_today = today_appointments.filter(status='completed').count()

    # Lab reports statistics
    total_lab_reports = LabReport.objects.count()
    recent_lab_reports = LabReport.objects.filter(uploaded_at__date=today).count()

    # Recent activity
    recent_appointments = Appointment.objects.select_related(
        'patient', 'doctor', 'doctor__user'
    ).order_by('-created_at')[:5]

    recent_lab_reports_list = LabReport.objects.select_related(
        'appointment', 'appointment__patient', 'doctor', 'doctor__user'
    ).order_by('-uploaded_at')[:5]

    # System health (placeholder metrics)
    system_health = 100  # Could be calculated based on various factors
    active_users_today = User.objects.filter(last_login__date=today).count()

    context = {
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_users': total_users,
        'total_appointments_today': total_appointments_today,
        'completed_today': completed_today,
        'total_lab_reports': total_lab_reports,
        'recent_lab_reports': recent_lab_reports,
        'recent_appointments': recent_appointments,
        'recent_lab_reports_list': recent_lab_reports_list,
        'system_health': system_health,
        'active_users_today': active_users_today,
        'today': today,
    }

    return render(request, 'admin_dash.html', context)


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
                appointment = Appointment.objects.get(
                    id=appointment_id,
                    doctor=request.user.doctor,
                    status__in=['scheduled', 'cancelled']  # Only allow active appointments
                )
                print(f"Found appointment: {appointment}")  # Debug
            except Appointment.DoesNotExist:
                print("Appointment not found")  # Debug
                return JsonResponse({'success': False, 'error': 'Appointment not found'})

            # Additional explicit check
            if appointment.status == 'cancelled':
                return JsonResponse({'success': False, 'error': 'Cannot prescribe for cancelled appointments'})

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
            appointment = Appointment.objects.get(
                id=appointment_id,
                doctor=request.user.doctor,
                status__in=['schedules', 'completed']
            )
            print(f"Doctor accessing prescription for their appointment")

        # Patients can view their own prescriptions
        elif request.user.user_type == 'patient':
            appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
            print(f"Patient accessing their own prescription")

        else:
            print("Access denied - invalid user type")
            return JsonResponse({'error': 'Access denied'}, status=403)

        # Additional chec for cancelled status
        if appointment.status == 'cancelled':
            return JsonResponse({'error': 'Cannot access prescriptions for cancelled appointments'}, status=403)

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


@login_required
def patient_lab_reports(request):
    """Patient view all their lab reports"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get all lab reports for this patient
    lab_reports = LabReport.objects.filter(
        appointment__patient=request.user
    ).select_related('appointment', 'appointment__doctor', 'appointment__doctor__user').order_by('-uploaded_at')

    # Calculate statistics
    total_reports = lab_reports.count()
    unique_doctors = lab_reports.values('appointment__doctor').distinct().count()
    latest_report = lab_reports.first()

    context = {
        'lab_reports': lab_reports,
        'total_reports': total_reports,
        'unique_doctors': unique_doctors,
        'latest_report': latest_report,
    }
    return render(request, 'patient_lab_reports.html', context)


@login_required
def patient_profile_update(request):
    """Update patient profile information"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        patient_profile = request.user.patient
    except Patient.DoesNotExist:
        messages.error(request, 'Patient profile not found.')
        return redirect('patient_dashboard')

    if request.method == 'POST':
        form = PatientProfileUpdateForm(request.POST, instance=patient_profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('dashboard')
    else:
        form = PatientProfileUpdateForm(instance=patient_profile, user=request.user)

    context = {
        'form': form,
        'patient_profile': patient_profile,
    }
    return render(request, 'patient_profile_update.html', context)


@login_required
def admin_doctors_list(request):
    """Admin view to list all doctors"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    specialization_filter = request.GET.get('specialization', '')

    # Get all doctors
    doctors = Doctor.objects.select_related('user').all()

    # Apply filters
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(specialization__icontains=search_query)
        )

    if specialization_filter:
        doctors = doctors.filter(specialization=specialization_filter)

    # Get specializations for filter dropdown
    specializations = Doctor.SPECIALIZATION_CHOICES

    context = {
        'doctors': doctors,
        'specializations': specializations,
        'search_query': search_query,
        'selected_specialization': specialization_filter,
        'total_doctors': doctors.count(),
    }
    return render(request, 'admin_doctors_list.html', context)


@login_required
def admin_doctor_detail(request, doctor_id):
    """Admin view for doctor details"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    doctor = get_object_or_404(Doctor, id=doctor_id)

    # Get doctor's recent appointments
    recent_appointments = Appointment.objects.filter(
        doctor=doctor
    ).select_related('patient').order_by('-appointment_date')[:10]

    # Get doctor's statistics
    total_appointments = Appointment.objects.filter(doctor=doctor).count()
    completed_appointments = Appointment.objects.filter(doctor=doctor, status='completed').count()
    today_appointments = Appointment.objects.filter(doctor=doctor, appointment_date=timezone.now().date()).count()

    context = {
        'doctor': doctor,
        'recent_appointments': recent_appointments,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'today_appointments': today_appointments,
    }
    return render(request, 'admin_doctor_detail.html', context)


@login_required
def admin_doctor_create(request):
    """Admin view to create new doctor"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        # Handle form submission
        user_form = DoctorUserForm(request.POST)
        doctor_form = DoctorProfileForm(request.POST)

        if user_form.is_valid() and doctor_form.is_valid():
            # Create user first
            user = user_form.save(commit=False)
            user.user_type = 'doctor'
            user.set_password('doctor123')  # Set default password
            user.save()

            # Create doctor profile
            doctor = doctor_form.save(commit=False)
            doctor.user = user
            doctor.save()

            messages.success(request, f'Doctor {user.get_full_name()} created successfully!')
            return redirect('admin_doctors_list')
    else:
        user_form = DoctorUserForm()
        doctor_form = DoctorProfileForm()

    context = {
        'user_form': user_form,
        'doctor_form': doctor_form,
    }
    return render(request, 'admin_doctor_create.html', context)


@login_required
def admin_doctor_edit(request, doctor_id):
    """Admin view to edit doctor"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    doctor = get_object_or_404(Doctor, id=doctor_id)

    if request.method == 'POST':
        user_form = DoctorUserForm(request.POST, instance=doctor.user)
        doctor_form = DoctorProfileForm(request.POST, instance=doctor)

        if user_form.is_valid() and doctor_form.is_valid():
            user_form.save()
            doctor_form.save()

            messages.success(request, f'Doctor {doctor.user.get_full_name()} updated successfully!')
            return redirect('admin_doctor_detail', doctor_id=doctor.id)
    else:
        user_form = DoctorUserForm(instance=doctor.user)
        doctor_form = DoctorProfileForm(instance=doctor)

    context = {
        'doctor': doctor,
        'user_form': user_form,
        'doctor_form': doctor_form,
    }
    return render(request, 'admin_doctor_edit.html', context)


@login_required
def admin_doctor_toggle_active(request, doctor_id):
    """Toggle doctor active status"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    doctor = get_object_or_404(Doctor, id=doctor_id)

    # For now, we'll use is_active on User model
    doctor.user.is_active = not doctor.user.is_active
    doctor.user.save()

    status = "activated" if doctor.user.is_active else "deactivated"
    messages.success(request, f'Doctor {doctor.user.get_full_name()} has been {status}.')

    return redirect('admin_doctors_list')


@login_required
def admin_patients_list(request):
    """Admin view to list all patients"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get search parameters
    search_query = request.GET.get('search', '')

    # Get all patients
    patients = Patient.objects.select_related('user').all()

    # Apply search filter
    if search_query:
        patients = patients.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__phone__icontains=search_query)
        )

    context = {
        'patients': patients,
        'search_query': search_query,
        'total_patients': patients.count(),
    }
    return render(request, 'admin_patients_list.html', context)


@login_required
def admin_patient_detail(request, patient_id):
    """Admin view for patient details"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    patient = get_object_or_404(Patient, id=patient_id)

    # Get patient's appointments
    appointments = Appointment.objects.filter(patient=patient.user).select_related(
        'doctor', 'doctor__user'
    ).order_by('-appointment_date')[:10]

    # Get patient's lab reports
    lab_reports = LabReport.objects.filter(appointment__patient=patient.user).select_related(
        'appointment', 'doctor', 'doctor__user'
    ).order_by('-uploaded_at')[:10]

    # Calculate statistics
    total_appointments = Appointment.objects.filter(patient=patient.user).count()
    completed_appointments = Appointment.objects.filter(patient=patient.user, status='completed').count()
    upcoming_appointments = Appointment.objects.filter(patient=patient.user, status='scheduled').count()
    total_lab_reports = LabReport.objects.filter(appointment__patient=patient.user).count()

    context = {
        'patient': patient,
        'appointments': appointments,
        'lab_reports': lab_reports,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'upcoming_appointments': upcoming_appointments,
        'total_lab_reports': total_lab_reports,
    }
    return render(request, 'admin_patient_detail.html', context)


@login_required
def admin_patient_toggle_active(request, patient_id):
    """Toggle patient active status"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    patient = get_object_or_404(Patient, id=patient_id)
    patient.user.is_active = not patient.user.is_active
    patient.user.save()

    status = "activated" if patient.user.is_active else "deactivated"
    messages.success(request, f'Patient {patient.user.get_full_name()} has been {status}.')

    return redirect('admin_patients_list')


# views.py - Add these views

@login_required
def admin_appointments_list(request):
    """Admin view to list and manage all appointments"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    doctor_filter = request.GET.get('doctor', '')
    search_query = request.GET.get('search', '')

    # Get all appointments with related data
    appointments = Appointment.objects.select_related(
        'patient', 'doctor', 'doctor__user'
    ).prefetch_related('prescription').order_by('-appointment_date', '-created_at')

    # Apply filters
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)

    if doctor_filter:
        appointments = appointments.filter(doctor_id=doctor_filter)

    if search_query:
        appointments = appointments.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    # Get doctors for filter dropdown
    doctors = Doctor.objects.select_related('user').all()

    # Calculate statistics
    total_appointments = appointments.count()
    scheduled_count = appointments.filter(status='scheduled').count()
    completed_count = appointments.filter(status='completed').count()
    cancelled_count = appointments.filter(status='cancelled').count()

    context = {
        'appointments': appointments,
        'doctors': doctors,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'doctor_filter': doctor_filter,
        'search_query': search_query,
        'total_appointments': total_appointments,
        'scheduled_count': scheduled_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'status_choices': ['scheduled', 'completed', 'cancelled'],
    }
    return render(request, 'admin_appointments_list.html', context)


@login_required
def admin_appointments_analytics(request):
    """Admin view for appointment analytics and insights"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Date range for analytics (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Get appointments in date range
    appointments = Appointment.objects.filter(
        appointment_date__range=[start_date, end_date]
    ).select_related('doctor', 'doctor__user')

    # Daily appointments count
    daily_counts = appointments.values('appointment_date').annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        scheduled=Count('id', filter=Q(status='scheduled')),
        cancelled=Count('id', filter=Q(status='cancelled'))
    ).order_by('appointment_date')

    # Doctor-wise statistics
    doctor_stats = appointments.values(
        'doctor__user__first_name',
        'doctor__user__last_name',
        'doctor__specialization'
    ).annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
    ).order_by('-total')

    # Calculate completion rate for each doctor
    for stat in doctor_stats:
        stat['completion_rate'] = (stat['completed'] * 100.0 / stat['total']) if stat['total'] > 0 else 0

    # Status distribution
    status_distribution = appointments.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Weekly trends - SQLite compatible
    weekly_trends = []
    current_date = start_date
    while current_date <= end_date:
        week_start = current_date
        week_end = current_date + timedelta(days=6)
        if week_end > end_date:
            week_end = end_date

        week_appointments = appointments.filter(
            appointment_date__range=[week_start, week_end]
        ).count()

        weekly_trends.append({
            'week': f"{week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}",
            'total': week_appointments
        })

        current_date = week_end + timedelta(days=1)

    # Peak hours analysis - SQLite compatible
    peak_hours = []
    for hour in range(8, 18):  # From 8 AM to 5 PM
        hour_appointments = appointments.filter(
            estimated_time__hour=hour
        ).count()

        if hour_appointments > 0:
            peak_hours.append({
                'estimated_time__hour': hour,
                'count': hour_appointments
            })

    # Sort by count descending
    peak_hours.sort(key=lambda x: x['count'], reverse=True)

    total_appointments_count = appointments.count()
    completed_appointments_count = appointments.filter(status='completed').count()
    completion_rate = (
                completed_appointments_count * 100.0 / total_appointments_count) if total_appointments_count > 0 else 0

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'daily_counts': list(daily_counts),
        'doctor_stats': doctor_stats,
        'status_distribution': list(status_distribution),
        'weekly_trends': weekly_trends,
        'peak_hours': peak_hours,
        'total_appointments': total_appointments_count,
        'completion_rate': completion_rate,
    }
    return render(request, 'admin_appointments_analytics.html', context)


@login_required
def admin_lab_reports_list(request):
    """Admin view to list and manage all lab reports"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Get filter parameters
    report_type_filter = request.GET.get('report_type', '')
    doctor_filter = request.GET.get('doctor', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')

    # Get all lab reports with related data
    lab_reports = LabReport.objects.select_related(
        'appointment',
        'appointment__patient',
        'doctor',
        'doctor__user'
    ).order_by('-uploaded_at')

    # Apply filters
    if report_type_filter:
        lab_reports = lab_reports.filter(report_type=report_type_filter)

    if doctor_filter:
        lab_reports = lab_reports.filter(doctor_id=doctor_filter)

    if date_from:
        lab_reports = lab_reports.filter(uploaded_at__date__gte=date_from)

    if date_to:
        lab_reports = lab_reports.filter(uploaded_at__date__lte=date_to)

    if search_query:
        lab_reports = lab_reports.filter(
            Q(test_name__icontains=search_query) |
            Q(appointment__patient__first_name__icontains=search_query) |
            Q(appointment__patient__last_name__icontains=search_query) |
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query) |
            Q(findings__icontains=search_query)
        )

    # Get doctors and report types for filter dropdowns
    doctors = Doctor.objects.select_related('user').all()
    report_types = LabReport.REPORT_TYPES

    # Calculate statistics
    total_reports = lab_reports.count()
    today_reports = lab_reports.filter(uploaded_at__date=timezone.now().date()).count()

    context = {
        'lab_reports': lab_reports,
        'doctors': doctors,
        'report_types': report_types,
        'report_type_filter': report_type_filter,
        'doctor_filter': doctor_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'total_reports': total_reports,
        'today_reports': today_reports,
    }
    return render(request, 'admin_lab_reports_list.html', context)


@login_required
def admin_lab_reports_statistics(request):
    """Admin view for lab reports statistics and insights"""
    if request.user.user_type != 'admin' and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Date range for statistics (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Get lab reports in date range
    lab_reports = LabReport.objects.filter(
        uploaded_at__date__range=[start_date, end_date]
    ).select_related('doctor', 'doctor__user', 'appointment', 'appointment__patient')

    # Report type distribution
    type_distribution = lab_reports.values('report_type').annotate(
        count=Count('id')
    ).order_by('-count')

    # Daily upload counts - SQLite compatible
    daily_uploads = []
    current_date = start_date
    while current_date <= end_date:
        day_count = lab_reports.filter(uploaded_at__date=current_date).count()
        if day_count > 0:
            daily_uploads.append({
                'upload_date': current_date,
                'count': day_count
            })
        current_date += timedelta(days=1)

    # Doctor-wise statistics
    doctor_stats = lab_reports.values(
        'doctor__user__first_name',
        'doctor__user__last_name',
        'doctor__specialization'
    ).annotate(
        total_reports=Count('id'),
        unique_patients=Count('appointment__patient', distinct=True)
    ).order_by('-total_reports')

    # Monthly trend - SQLite compatible
    monthly_trend = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        # Calculate end of month
        if current_month.month == 12:
            next_month = current_month.replace(year=current_month.year + 1, month=1, day=1)
        else:
            next_month = current_month.replace(month=current_month.month + 1, day=1)

        month_end = next_month - timedelta(days=1)
        if month_end > end_date:
            month_end = end_date

        month_count = lab_reports.filter(
            uploaded_at__date__range=[current_month, month_end]
        ).count()

        monthly_trend.append({
            'year': current_month.year,
            'month': current_month.month,
            'count': month_count
        })

        current_month = next_month

    # Most common tests
    common_tests = lab_reports.values('test_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    total_reports_count = lab_reports.count()
    unique_patients_count = lab_reports.values('appointment__patient').distinct().count()
    unique_doctors_count = lab_reports.values('doctor').distinct().count()

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'type_distribution': list(type_distribution),
        'daily_uploads': daily_uploads,
        'doctor_stats': doctor_stats,
        'monthly_trend': monthly_trend,
        'common_tests': list(common_tests),
        'total_reports': total_reports_count,
        'unique_patients': unique_patients_count,
        'unique_doctors': unique_doctors_count,
    }
    return render(request, 'admin_lab_reports_statistics.html', context)