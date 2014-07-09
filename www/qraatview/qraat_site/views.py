from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from hello.models import tx_ID, TxAlias, TxPulse

# Create your views here.


def index(request):
    nav_options = get_nav_options(request)

    return render(
        request, "qraat_site/index.html",
        {'nav_options': nav_options})


@login_required(login_url='/auth/login')
def transmitters(request):
    nav_options = get_nav_options(request)
    transmitters = tx_ID.objects.all()

    return render(request, "qraat_site/transmitters.html",
            {"transmitters": transmitters, 'nav_options': nav_options})


def regular_content(request):
    return redirect('/hello/index.html') 


def get_nav_options(request):
    nav_options = [{"url": "/qraat/regular-content", "name": "Regular content"}]

    if request.user.is_authenticated():
        user = request.user
        if user.is_superuser:
            nav_options.append({"url": "/qraat/transmitters",
                                "name": "Transmitters"})
    return nav_options
