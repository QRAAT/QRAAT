"""This is the views module for qraat_auth

This module contains all views for users account changing, login, etc.
"""

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from qraat_auth.forms import AccountChangeForm
from qraat_auth.forms import PasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

# Create your views here.


def index(request):
    """Auth index, it checks for logged in users and redirects to a
    login page if necessary."""

    if not request.user.is_authenticated():
        return redirect('login/?next=%s' % request.path)
    return redirect('/')


def user_logout(request):
    """This view handles the user logout."""

    if request.user.is_authenticated():
        logout(request)

    return redirect("/")


def user_login(request):
    """This view handles user login.
    It has a next parameter in case of redirecting a
    user to a requested page"""

    next = request.GET.get("next")

    if request.method == 'POST':
        login_form = AuthenticationForm(data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if next != "None":
                        return redirect(next)
                    else:
                        return redirect('/')
                else:
                    return HttpResponse("Innactive user!")
    else:
        login_form = AuthenticationForm()

    return render(
        request, 'qraat_auth/loginform.html', {'login_form': login_form,
                                               'next': next})


@login_required(login_url='/auth')
def show_users(request):
    """This view shows a list of registered users in the system.
    It is for admin use only"""

    user = request.user
    if request.method == 'GET':

        if user.is_superuser:
            users = User.objects.all()
            return render(
                request, 'qraat_auth/users.html',
                {'users': users})
        else:
            return HttpResponse("Restricted area!")

    return HttpResponse("Try a get!")


@login_required(login_url='/auth')
def user_account(request, user_id=None):
    """This view displays user account information"""

    if request.user.is_superuser and user_id:
        user = User.objects.get(id=user_id)
    else:
        user = request.user

    return render(
        request, 'qraat_auth/user-account.html', {'user': user})


@login_required(login_url='/auth')
def edit_account(request):
    """This view is the entry for a form to edit user's information."""

    user = request.user
    form = AccountChangeForm(instance=user)

    if request.method == 'POST':
        form = AccountChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return render(
                request, 'qraat_auth/edit-account.html',
                {'form': form, 'changed': True})

    return render(request, 'qraat_auth/edit-account.html', {'form': form})


@login_required(login_url='/auth')
def change_password(request):
    """This view is the entry for users to change their password"""

    user = request.user
    form = PasswordChangeForm(instance=user)

    if request.method == 'POST':
        form = PasswordChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return render(
                request, 'qraat_auth/change-password.html',
                {'form': form, 'changed': True})

    return render(request, 'qraat_auth/change-password.html', {'form': form})
