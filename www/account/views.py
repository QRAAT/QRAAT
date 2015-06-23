"""This is the views module for qraat_auth

This module contains all views for users account changing, login, etc.
"""

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from account.forms import AccountChangeForm
from account.forms import PasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
import re #regular expressions

# Create your views here.


def index(request):
    """Auth index, it checks for logged in users and redirects to a
    login page if necessary."""

    if not request.user.is_authenticated():
        return redirect('login/?next=%s' % request.get_full_path())
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

    full_path = request.get_full_path() #gets path and form data
    
    if full_path != request.path: #true when next parameter is set
				next_regex = re.compile(".*?next=(.*)")
				next_regex_results = next_regex.search(full_path)
				next_URL = next_regex_results.group(1) #get contents of request.get_full_path() after ?next=
    else:
        next_URL = "None"

    if request.method == 'POST':
        login_form = AuthenticationForm(data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if next_URL != "None":
                        return redirect(next_URL)
                    else:
                        return redirect('/')
                else:
                    """Special case of Http403 (inactive user) - 
                    error for this case is caught in loginform.html"""
    else:
        login_form = AuthenticationForm()

    return render(
        request, 'account/loginform.html', {'login_form': login_form,
                                               'next': next_URL})


@login_required(login_url='/account/login')
def show_users(request):
    """This view shows a list of registered users in the system.
    It is for admin use only"""

    user = request.user
    if request.method == 'GET':

        if user.is_superuser:
            users = User.objects.all()
            return render(
                request, 'account/users.html',
                {'users': users})
        else:
					  raise PermissionDenied #403

    return HttpResponse("Try a get!")


@login_required(login_url='/account/login')
def user_account(request, user_id=None):
    """This view displays user account information"""

    if request.user.is_superuser and user_id:
        user = User.objects.get(id=user_id)
    else:
        user = request.user

    return render(
        request, 'account/user-account.html', {'user': user})


@login_required(login_url='/account/login')
def edit_account(request):
    """This view is the entry for a form to edit user's information."""

    user = request.user
    form = AccountChangeForm(instance=user)

    if request.method == 'POST':
        form = AccountChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return render(
                request, 'account/edit-account.html',
                {'form': form, 'changed': True})

    return render(request, 'account/edit-account.html', {'form': form})


@login_required(login_url='/account/login')
def change_password(request):
    """This view is the entry for users to change their password"""

    user = request.user
    form = PasswordChangeForm(instance=user)

    if request.method == 'POST':
        form = PasswordChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return render(
                request, 'account/change-password.html',
                {'form': form, 'changed': True})

    return render(request, 'account/change-password.html', {'form': form})
