from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

# Register your models here.

from qraat_auth.models import QraatUser


class UserForm(forms.ModelForm):

    # A form for creating new users. Includes all the required
    # fields, plus a repeated password.

    password1 = forms.CharField(
        label='Password', widget=forms.PasswordInput)

    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = QraatUser
        fields = ("email", "first_name", "last_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")

        return password2

    def clean_username(self):
        username = self.cleaned_data.get("email")
        user = None

        try:
            user = QraatUser.objects.get(email=username)
        except Exception:
            if user is not None:
                raise forms.ValidationError("Email already exists")
            else:
                return username

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AccountChangeForm(forms.ModelForm):
    class Meta:
        model = QraatUser
        fields = ("first_name", "last_name")


class PasswordChangeForm(forms.ModelForm):
    cur_password = forms.CharField(
        label='Current password', widget=forms.PasswordInput)

    password1 = forms.CharField(
        label='New password', widget=forms.PasswordInput)

    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = QraatUser
        fields = ()

    def clean_cur_password(self):
        cur_password = self.cleaned_data.get("cur_password")
        user = super(PasswordChangeForm, self).save(commit=False)
        if cur_password and not user.check_password(cur_password):
            raise forms.ValidationError("Current password doesn't match")

        return cur_password

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")

        return password2

    def save(self, commit=True):
        user = super(PasswordChangeForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class QraatUserChangeForm(forms.ModelForm):
    # A form for updating users. Includes all the fields on
    # the user, but replaces the password field with admin's
    # password hash display field.
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = QraatUser
        fields = (
            "email", "first_name", "last_name",
            "password", "is_active", "is_admin")

    def clean_password(self):
        return self.initial["password"]
