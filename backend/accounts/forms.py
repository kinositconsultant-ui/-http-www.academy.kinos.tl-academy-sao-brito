from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import School, User


class StyledAuthForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "block w-full rounded-md border-0 py-2 px-3 text-zinc-900 shadow-sm ring-1 ring-inset ring-zinc-300 placeholder:text-zinc-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm",
            "placeholder": "Username",
            "data-testid": "login-username-input",
            "autofocus": True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "block w-full rounded-md border-0 py-2 px-3 text-zinc-900 shadow-sm ring-1 ring-inset ring-zinc-300 placeholder:text-zinc-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm",
            "placeholder": "Password",
            "data-testid": "login-password-input",
        })
    )


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "registration_no", "address", "phone", "email",
                  "website", "founded_date", "motto", "logo", "currency"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "founded_date": forms.DateInput(attrs={"type": "date"}),
        }


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, required=False,
        help_text="Leave blank to keep current password."
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role",
                  "phone", "address", "is_active"]

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get("password")
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user
