from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from hospital.models import Doctor


# Create your views here.
def index(request):
    return HttpResponse("<h1>Welcome to Hospital Management Application</h1>")

def view_doctors(request):
    doctors = Doctor.objects.all().select_related('user')
    return render(request,'doctors.html', {'doctors': doctors})