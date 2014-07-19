from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from qraat_site.models import Project, Tx, Location
from django.core.exceptions import ObjectDoesNotExist
from qraat_site.forms import ProjectForm, EditProjectForm


def index(request):
    nav_options = get_nav_options(request)
    projects = Project.objects.filter(is_public=True, is_hidden=False)

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
def show_transmitter(request, project_id, transmitter_id):
    tx = Tx.objects.get(ID=transmitter_id)
    return HttpResponse(
        "Transmitter: %d Model: %s Manufacturer: %s" % (
            tx.ID, tx.tx_makeID.model, tx.tx_makeID.manufacturer))


@login_required(login_url='auth/login')
def show_location(request, project_id, location_id):
    location = Location.objects.get(ID=location_id)
    return HttpResponse(
        "Location: %s location: %s" % (location.name, location.location))


@login_required(login_url='/auth/login')
def projects(request):
    user = request.user

    user_projects = Project.objects.filter(ownerID=user.id)
    public_projects = Project.objects.filter(is_public=True, is_hidden=False)

    nav_options = get_nav_options(request)

    return render(request, 'qraat_site/projects.html',
                  {'public_projects': public_projects,
                   'user_projects': user_projects,
                   'nav_options': nav_options})


@login_required(login_url='/auth/login')
def create_project(request):

    nav_options = get_nav_options(request)

    if request.method == 'POST':

        user = request.user
        form = ProjectForm(user=user, data=request.POST)

        if form.is_valid():
            project = form.save()
            Group.objects.create(name="%d_viewers" % project.ID)
            Group.objects.create(name="%d_collaborators" % project.ID)

            return redirect('/qraat/project/%d' % project.ID)
    else:
        form = ProjectForm()

    return render(request, 'qraat_site/create-project.html',
                  {'form': form,
                   'nav_options': nav_options})


@login_required(login_url='/auth/login')
def edit_project(request, project_id):

    nav_options = get_nav_options(request)

    user = request.user

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
        return HttpResponse("Error: We did not find this project")

    else:
        if user.id == project.ownerID:
            if request.method == 'POST':
                form = EditProjectForm(data=request.POST, instance=project)
                if form.is_valid():
                    form.save()
                    return render(
                        request, 'qraat_site/edit-project.html',
                        {'nav_options': nav_options,
                         'changed': True,
                         'form': form})
            else:
                form = EditProjectForm(instance=project)

            return render(
                request, 'qraat_site/edit-project.html',
                {'nav_options': nav_options,
                 'form': form})

        else:
            return HttpResponse(
                "Just the project owner can access this page")


def show_project(request, project_id):

    nav_options = get_nav_options(request)

    try:
        project = Project.objects.get(ID=project_id)

        if project.is_public:
            return render(
                request, 'qraat_site/display-project.html',
                {'project': project,
                 'nav_options': nav_options})

        else:
            return HttpResponse("Project is not public")
    except ObjectDoesNotExist:
        return HttpResponse("Project not found")


def regular_content(request):
    return redirect('/hello/index.html')


def get_nav_options(request):
    nav_options = []

    if request.user.is_authenticated():
        nav_options.append({"url": "/qraat/projects",
                            "name": "Projects"})
    return nav_options
