from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Patient, LabReport


class PatientRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=10, required=True)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(widget=forms.Textarea)
    emergency_contact = forms.CharField(max_length=10, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2',
                  'first_name', 'last_name', 'phone']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'patient'
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data['phone']

        if commit:
            user.save()
            # Create patient profile
            Patient.objects.create(
                user=user,
                date_of_birth=self.cleaned_data['date_of_birth'],
                address=self.cleaned_data['address'],
                emergency_contact=self.cleaned_data['emergency_contact']
            )
        return user


class LabReportForm(forms.ModelForm):
    class Meta:
        model = LabReport
        fields = ['report_type', 'test_name', 'report_file', 'findings', 'notes']
        widgets = {
            'findings': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }