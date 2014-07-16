from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from hello.models import tx_ID, TxAlias, TxPulse, TxDeployment
from qraat_site.models import Project
from django.core.exceptions import ObjectDoesNotExist


def index(request):
    nav_options = get_nav_options(request)
    projects = []

    for project in Project.objects.all():
        if not project.is_hidden and project.is_public:
            projects.append(project)

    return render(
        request, "qraat_site/index.html",
        {'nav_options': nav_options,
         'projects': projects})


@login_required(login_url='/auth/login')
def transmitters(request):
    nav_options = get_nav_options(request)
    tx_IDs = tx_ID.objects.all()
    transmitters = []

    for tx in tx_IDs:
        pulses = TxPulse.objects.filter(tx_ID=tx)
        deployments = TxDeployment.objects.filter(tx_ID=tx)
        aliases = TxAlias.objects.filter(tx_ID=tx)
        transmitter = {}
        transmitter["transmitter"] = tx
        transmitter["pulses"] = pulses
        transmitter["deployments"] = deployments
        transmitter["aliases"] = aliases
        transmitters.append(transmitter)

    return render(
        request, "qraat_site/transmitters.html",
        {"transmitters": transmitters, 'nav_options': nav_options})


@login_required(login_url='/auth/login')
def get_transmitter(request, transmitter_id):
    tx = tx_ID.objects.get(ID=transmitter_id)
    return HttpResponse(
        "Transmitter: %d Model: %s Manufacturer: %s" % (
            tx.ID, tx.tx_info_ID.model, tx.tx_info_ID.manufacturer))


def show_project(request, project_id):
    try:
        project = Project.objects.get(ID=project_id)

        if project.is_public:
            return render(
                request, 'qraat_site/display-project.html',
                {'project': project})

        else:
            return HttpResponse("Project is not public")
    except ObjectDoesNotExist:
        return HttpResponse("Project not found")


def regular_content(request):
    return redirect('/hello/index.html')


def get_nav_options(request):
    nav_options = [{"url": "/qraat/regular-content",
                    "name": "Regular content"}]

    if request.user.is_authenticated():
        user = request.user
        if user.is_superuser:
            nav_options.append({"url": "/qraat/transmitters",
                                "name": "Transmitters"})
    return nav_options
