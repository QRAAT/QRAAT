from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from qraat_auth.forms import UserForm
from django.contrib.auth.forms import AuthenticationForm

import traceback

# Create your views here.

def index(request):
	if not request.user.is_authenticated():
		return redirect('login/')#?next=%s' % request.path)
	return redirect('login/logged-in')


def user_logout(request):
	if request.user.is_authenticated():
		logout(request)
	
	return HttpResponse("Your're logged out!")

def user_login(request):
	if request.method == 'POST':
		login_form = AuthenticationForm(data=request.POST)
		if login_form.is_valid():
			user = login_form.get_user()
			if user is not None:
				if user.is_active:
					login(request, user)
					return HttpResponseRedirect('logged-in')
				else:
					return HttpResponse("Innactive user!")	
	else:
		login_form = AuthenticationForm()

	return render(request, 'qraat_auth/loginform.html', {'login_form': login_form})		


@login_required(login_url='/auth')
def user_logged_in(request):
	username = request.user.username
	return render(request, 'qraat_auth/loggedin.html', {'username': username})
	

def createUserForm(request):
	content = {}

	if request.method == 'POST':
		user_form = UserForm(request.POST)
		content['user_form'] = user_form
		if user_form.is_valid():
			#creates user here
			#form.cleaned_data as required
			username = user_form.clean_username()
			password = user_form.clean_password2()
			user_form.save()

			user = authenticate(username=username, 
					password=password)

			login(request, user)

			return HttpResponseRedirect('user-created')
					
	else:
		content['user_form'] = UserForm()

	return render(request, 'qraat_auth/newuserform.html', {'content': content})	

def userCreated(request):
	return HttpResponse("User Created!")

