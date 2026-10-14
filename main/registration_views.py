from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import redirect, render

from .models import Student, Faculty, Department, Course
from .registration_forms import (
    StudentRegistrationForm,
    FacultyRegistrationForm,
)


def student_register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            Student.objects.create(
                student_id=data["account_id"],
                name=data["name"].strip(),
                email=data["email"].strip(),
                password=make_password(data["password"]),
                role="Student",
                department=data["department"],
            )
            messages.success(
                request,
                "Student account created successfully. You can now sign in.",
            )
            return redirect("std_login")
    else:
        form = StudentRegistrationForm()

    return render(request, "registration_form.html", {
        "form": form,
        "account_type": "Student",
        "page_title": "Create your student account",
        "subtitle": "Join your courses and keep your learning organized.",
        "login_url_name": "std_login",
    })


def faculty_register(request):
    if request.method == "POST":
        form = FacultyRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            Faculty.objects.create(
                faculty_id=data["account_id"],
                name=data["name"].strip(),
                email=data["email"].strip(),
                password=make_password(data["password"]),
                role="Faculty",
                department=data["department"],
            )
            messages.success(
                request,
                "Faculty account created successfully. You can now sign in.",
            )
            return redirect("std_login")
    else:
        form = FacultyRegistrationForm()

    return render(request, "registration_form.html", {
        "form": form,
        "account_type": "Faculty",
        "page_title": "Create your faculty account",
        "subtitle": "Prepare your teaching workspace and connect with learners.",
        "login_url_name": "std_login",
    })


@staff_member_required
def admin_dashboard(request):
    context = {
        "student_count": Student.objects.count(),
        "faculty_count": Faculty.objects.count(),
        "department_count": Department.objects.count(),
        "course_count": Course.objects.count(),
        "recent_students": Student.objects.order_by("-student_id")[:5],
        "recent_faculty": Faculty.objects.order_by("-faculty_id")[:5],
    }
    return render(request, "admin_dashboard.html", context)
