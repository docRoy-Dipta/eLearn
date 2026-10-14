from django import forms
from django.core.validators import RegexValidator
from django.db.models import Q

from .models import Department, Student, Faculty


class BaseRegistrationForm(forms.Form):
    account_id = forms.IntegerField(
        label="Student / Faculty ID",
        min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your numeric ID",
        }),
    )
    name = forms.CharField(
        max_length=100,
        label="Full name",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your full name",
            "autocomplete": "name",
        }),
    )
    email = forms.EmailField(
        max_length=100,
        label="Email address",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        empty_label="Select your department",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password = forms.CharField(
        min_length=8,
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "At least 8 characters",
            "autocomplete": "new-password",
        }),
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Re-enter your password",
            "autocomplete": "new-password",
        }),
    )

    account_model = None
    id_field = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.order_by("name")

    def clean_account_id(self):
        account_id = self.cleaned_data["account_id"]
        if self.account_model.objects.filter(
            **{self.id_field: account_id}
        ).exists():
            raise forms.ValidationError(
                "This ID is already registered. Please use another ID."
            )
        return account_id

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if self.account_model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "This email is already registered for this account type."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "The passwords do not match.")

        return cleaned_data


class StudentRegistrationForm(BaseRegistrationForm):
    account_model = Student
    id_field = "student_id"


class FacultyRegistrationForm(BaseRegistrationForm):
    account_model = Faculty
    id_field = "faculty_id"
