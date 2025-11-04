from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User, Patient, LabReport, Doctor


class PatientRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )
    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 10-digit phone number'})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    gender = forms.ChoiceField(  # Updated to ChoiceField
        choices=Patient.GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter your complete address'})
    )
    emergency_contact = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact number'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2',
                  'first_name', 'last_name', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'patient'
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data['phone']

        if commit:
            user.save()
            # Create patient profile with gender
            Patient.objects.create(
                user=user,
                date_of_birth=self.cleaned_data['date_of_birth'],
                gender=self.cleaned_data['gender'],  # Add gender here
                address=self.cleaned_data['address'],
                emergency_contact=self.cleaned_data['emergency_contact']
            )
        return user

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and (len(phone) != 10 or not phone.isdigit()):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_emergency_contact(self):
        emergency_contact = self.cleaned_data.get('emergency_contact')
        if emergency_contact and (len(emergency_contact) != 10 or not emergency_contact.isdigit()):
            raise forms.ValidationError("Emergency contact must be exactly 10 digits.")
        return emergency_contact


class PatientProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )
    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 10-digit phone number'})
    )

    class Meta:
        model = Patient
        fields = ['date_of_birth', 'gender', 'address', 'emergency_contact']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter your complete address'}),
            'emergency_contact': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Emergency contact number'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Prepopulate user fields if user is provided
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
            self.fields['phone'].initial = self.user.phone

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and (len(phone) != 10 or not phone.isdigit()):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_emergency_contact(self):
        emergency_contact = self.cleaned_data.get('emergency_contact')
        if emergency_contact and (len(emergency_contact) != 10 or not emergency_contact.isdigit()):
            raise forms.ValidationError("Emergency contact must be exactly 10 digits.")
        return emergency_contact

    def save(self, commit=True):
        patient = super().save(commit=False)

        # Update user information
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            self.user.phone = self.cleaned_data['phone']
            if commit:
                self.user.save()

        if commit:
            patient.save()

        return patient


class PatientProfileImageForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_image']
        widgets = {
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        if image:
            # Validate file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 5MB )")
            # Validate file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            extension = image.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError("Unsupported file extension. Please use JPG, PNG, or GIF.")
        return image


class PatientPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        })
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    class Meta:
        fields = ['old_password', 'new_password1', 'new_password2']


class LabReportForm(forms.ModelForm):
    class Meta:
        model = LabReport
        fields = ['report_type', 'test_name', 'report_file', 'findings', 'notes']
        widgets = {
            'findings': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class DoctorUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
        }


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['qualification', 'specialization', 'start_time', 'end_time', 'available_days', 'max_appointments']
        widgets = {
            'qualification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MBBS, MD'}),
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'available_days': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g., Monday,Tuesday,Wednesday'}),
            'max_appointments': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '100'}),
        }

    def clean_available_days(self):
        days = self.cleaned_data.get('available_days')
        if days:
            # Validate days format
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            input_days = [day.strip().lower() for day in days.split(',')]

            for day in input_days:
                if day not in valid_days:
                    raise forms.ValidationError(f"Invalid day: {day}. Please use comma-separated day names.")

        return days