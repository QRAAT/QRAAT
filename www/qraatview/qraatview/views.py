from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from models import Project, Tx, Location
from forms import ProjectForm, EditProjectForm, AddTransmitterForm
from forms import AddManufacturerForm, AddTargetForm
from forms import AddDeploymentForm, AddLocationForm


def index(request):
    nav_options = get_nav_options(request)
    projects = Project.objects.filter(is_public=True, is_hidden=False)

    return render(
        request, "qraat_site/index.html",
        {'nav_options': nav_options,
         'projects': projects})


# @login_required(login_url='/auth/login')
# def transmitters(request):
#     nav_options = get_nav_options(request)
#     tx_IDs = tx_ID.objects.all()
#     transmitters = []

#     for tx in tx_IDs:
#         pulses = TxPulse.objects.filter(tx_ID=tx)
#         deployments = TxDeployment.objects.filter(tx_ID=tx)
#         aliases = TxAlias.objects.filter(tx_ID=tx)
#         transmitter = {}
#         transmitter["transmitter"] = tx
#         transmitter["pulses"] = pulses
#         transmitter["deployments"] = deployments
#         transmitter["aliases"] = aliases
#         transmitters.append(transmitter)

#     return render(
#         request, "qraat_site/transmitters.html",
#         {"transmitters": transmitters, 'nav_options': nav_options})


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
    public_projects = [p for p in Project.objects.filter(
        is_public=True, is_hidden=False) if p not in user_projects]

    nav_options = get_nav_options(request)

    return render(request, 'qraat_site/projects.html',
                  {'public_projects': public_projects,
                   'user_projects': user_projects,
                   'nav_options': nav_options})


def render_project_form(
        request, project_id, post_form, get_form, template_path, success_url):

    user = request.user
    nav_options = get_nav_options(request)
    thereis_newelement = None
    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
        return HttpResponse("Error: We did not find this project")

    else:
        if user.id == project.ownerID:
            if request.method == 'POST':
                form = post_form
                form.set_project(project)
                if form.is_valid():
                    form.save()
                    return redirect(success_url)

            elif request.method == 'GET':
                thereis_newelement = request.GET.get("new_element")
                form = get_form
                form.set_project(project)

            return render(request, template_path,
                          {"form": form,
                           "nav_options": nav_options,
                           "changed": thereis_newelement,
                           "project": project})
        else:
            return HttpResponse("Action not allowed")


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

            return redirect('/project/%d' % project.ID)
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
                         'form': form,
                         'project': project})
            else:
                form = EditProjectForm(instance=project)

            return render(
                request, 'qraat_site/edit-project.html',
                {'nav_options': nav_options,
                 'form': form,
                 'project': project})

        else:
            return HttpResponse(
                request, "Just the project owner can access this page")


@login_required(login_url="/auth/login")
def add_manufacturer(request, project_id):
    user = request.user
    nav_options = get_nav_options(request)
    istherenew_make = None

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
        return HttpResponse("Error: we didn't find this project")

    else:
        if user.id == project.ownerID and user.is_superuser:
            transmitter_form = AddTransmitterForm()
            if request.method == 'POST':
                manufacturer_form = AddManufacturerForm(data=request.POST)

                if manufacturer_form.is_valid():
                    make_obj = manufacturer_form.save()
                    return redirect(
                        "../add-manufacturer?newmake=\
                                True?makeid=%d" % make_obj.ID)

            elif request.method == 'GET':
                istherenew_make = request.GET.get("newmake")
                manufacturer_form = AddManufacturerForm()

            return render(
                request, "qraat_site/create-manufacturer.html",
                {"nav_options": nav_options,
                 "manufacturer_form": manufacturer_form,
                 "transmitter_form": transmitter_form,
                 "changed": istherenew_make,
                 "project": project})
        else:
            return HttpResponse("You are not allowed to do this.")


@login_required(login_url="auth/login")
def add_location(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddLocationForm(data=request.POST),
        get_form=AddLocationForm(),
        template_path="qraat_site/create-location.html",
        success_url="../add-location?new_element=True")


@login_required(login_url="/auth/login")
def add_transmitter(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddTransmitterForm(data=request.POST),
        get_form=AddTransmitterForm(),
        template_path="qraat_site/create-transmitter.html",
        success_url="../add-transmitter?new_element=True")


@login_required(login_url="/auth/login")
def add_target(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddTargetForm(data=request.POST),
        get_form=AddTargetForm(),
        template_path="qraat_site/create-target.html",
        success_url="../add-target?new_element=True")


@login_required(login_url="/auth/login")
def add_deployment(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddDeploymentForm(data=request.POST),
        get_form=AddDeploymentForm(),
        template_path="qraat_site/create-deployment.html",
        success_url="../add-deployment?new_element=True")


def show_project(request, project_id):

    nav_options = get_nav_options(request)
    user = request.user

    try:
        project = Project.objects.get(ID=project_id)

        if project.is_public:
            return render(
                request, 'qraat_site/display-project.html',
                {'project': project,
                 'nav_options': nav_options})

        else:
            if user.id == project.ownerID:
                return render(
                    request,
                    'qraat_site/display-project.html',
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
    user = request.user

    if user.is_authenticated():
        if user.is_superuser:
            nav_options.append(
                {"url": "auth:users",
                 "name": "Users"})

        nav_options.append({"url": "qraat:projects",
                            "name": "Projects"})

    return nav_options
