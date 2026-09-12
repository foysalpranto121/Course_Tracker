from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Course, Task, UserProfile


class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "profile_picture",
            "institution",
            "phone_number",
            "occupation",
            "learning_goal",
            "bio",
            "github_url",
        ]
        widgets = {
            "profile_picture": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "institution": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. University / Organization"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. +8801700000000"}),
            "occupation": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Student, Software Developer"}),
            "learning_goal": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Master Full-Stack Web Dev"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Tell us about your learning journey..."}),
            "github_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://github.com/yourusername"}),
        }



class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your email address",
        }),
    )

    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = "form-control"
            if field_name == "username":
                field.widget.attrs["placeholder"] = "Choose a username"


class SignInForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your username",
            "autofocus": True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your password",
        })
    )



class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "instructor",
            "instructor_email",
            "category",
            "start_date",
            "end_date",
            "progress",
            "status",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter course title",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Enter course description",
                "rows": 4,
            }),
            "instructor": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Instructor name",
            }),
            "instructor_email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "instructor@example.com",
            }),
            "category": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Web Development",
            }),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "progress": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "max": 100,
            }),
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
        }

    def clean_progress(self):
        progress = self.cleaned_data["progress"]

        if progress < 0 or progress > 100:
            raise forms.ValidationError(
                "Progress must be between 0 and 100."
            )

        return progress

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "End date cannot be earlier than start date."
            )

        return cleaned_data


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "due_date",
            "completed",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter task title",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Enter task description",
                "rows": 4,
            }),
            "due_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "completed": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }