from django import forms
from .models import Course, Task


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "instructor",
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
            "course",
            "title",
            "description",
            "due_date",
            "completed",
        ]

        widgets = {
            "course": forms.Select(attrs={
                "class": "form-select",
            }),
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