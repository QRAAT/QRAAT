import json
import project.utils
import project.rest_api
from django.db.models import Q
from django.db import connection
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.http import HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core import serializers
from django.template import Context
from project.models import Project, Tx, Location
from project.models import Target, Deployment
#from project.models import Site, Telemetry, Est
from project.forms import ProjectForm, OwnersEditProjectForm, AddTransmitterForm
from project.forms import AddManufacturerForm, AddTargetForm
from project.forms import AddDeploymentForm, AddLocationForm
from project.forms import EditTargetForm, EditTransmitterForm, EditLocationForm
from project.forms import EditDeploymentForm, EditProjectForm
#from project.forms import TelemetryGraphForm, EstGraphForm, ProcessingGraphForm
from viewsutils import *

import time
from calendar import timegm
from datetime import datetime

#from graph_views import * # graph_home, telemetry_graphs, etc. and helper functions

def index(request):
    """This view renders the system's first page.
    This page has a nav bar and users projects

    :param request: Django's http request object
    :type request: HttpRequest.
    :returns:  HttpResponse -- Rendered http response object
    """

    nav_options = get_nav_options(request)
    user = request.user

    if user.is_authenticated():
        return projects(request)
    else:
        public_projects = Project.objects.filter(
            is_public=True, is_hidden=False)

        return render(
            request, "project/index.html",
            {'nav_options': nav_options,
             'projects': public_projects})


def get_project(project_id):
    """Function for intern use that queries a project by id

    :param project_id: A valid project id
    :type project_id: int.

    :returns:  Project -- A Project Model instance
    """

    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
                raise Http404
    else:
        return project


def show_transmitter(request, project_id, transmitter_id):
    """
    This view renders transmitter's information

    :param request:  Django's request obj.
    :type request: HttpRequest.
    :param project_id:  Id for transmitter's project.
    :type project_id: int.
    :param transmitter_id:  Transmitter's id.
    :type transmitter_id: int.
    :returns:  HttpResponse -- Serialized http response with \
            transmitter's information.

    .. note::

       #TODO: Implement a nice view with a map in qraat_ui.
    """

    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        query = get_query("transmitter")
        tx = query(transmitter_id)
        return HttpResponse(
            "Transmitter: %d Model: %s Manufacturer: %s" % (
                tx.ID, tx.tx_makeID.model, tx.tx_makeID.manufacturer))
    else:
        return not_allowed_page(request)


def show_deployment(request, project_id, deployment_id):
    """
    This view renders deployment's information

    :param request:  Django's request obj.
    :type request: HttpRequest.
    :param project_id:  Id for deployment's project.
    :type project_id: int.
    :param transmitter_id:  Deployment's id.
    :type deployment_id: int.
    :returns:  HttpResponse -- Http response with rendered \
            deployment's information placed in qraat_ui.views.view_by_dep
    """

    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        return redirect(
            reverse("map:view_by_dep", args=(project_id, deployment_id))
            )
    else:
        return not_allowed_page(request)


def show_target(request, project_id, target_id):
    """
    This view renders target's information

    :param request:  Django's request obj.
    :type request: HttpRequest.
    :param project_id:  Id for target's project.
    :type project_id: int.
    :param target_id:  Target's id.
    :type target_id: int.
    :returns:  HttpResponse -- Serialized http response with \
            target's information.

    .. note::

       #TODO: Implement a nice view with a map in qraat_ui.
    """

    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        query = get_query("target")
        target = query(target_id)
        return HttpResponse(target)
    else:
        return not_allowed_page(request)


def show_location(request, project_id, location_id):
    """
    This view renders location's information

    :param request:  Django's request obj.
    :type request: HttpRequest.
    :param project_id:  Id for location's project.
    :type project_id: int.
    :param location_id:  Location's id.
    :type location_id: int.
    :returns:  HttpResponse -- Serialized http response with \
            location's information.

    .. note::

       #TODO: Implement a nice view with a map in qraat_ui.
    """

    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        query = get_query("location")
        location = query(location_id)

        return HttpResponse(
            "Location: %s location: %s" % (location.name, location.location))
    else:
        return not_allowed_page(request)


@login_required(login_url='/account/login')
def projects(request):
    """This view renders a page with projects.
    For a user projects are displayed as public projects,
    projects the user owns, projects the user can collaborate,
    and projects the user can visualize.

    :param request: Django's http request object
    :type request: HttpRequest.
    :returns:  HttpResponse -- Rendered http response object
    """

    user = request.user

    user_projects = Project.objects.filter(
        ownerID=user.id).exclude(is_hidden=True)

    collaborate_with = [project
                        # exclude hidden projects or owned projects
                        for project in Project.objects.exclude(
                            Q(ownerID=user.id) | Q(is_hidden=True))
                        if project.is_collaborator(user)]

    can_visualize = [project
                     for project in Project.objects.exclude(
                         Q(ownerID=user.id) | Q(is_hidden=True))
                     if project not in collaborate_with
                     and project.is_viewer(user)]

    public_projects = [p for p in Project.objects.filter(
        is_public=True, is_hidden=False) if p not in user_projects
        and p not in collaborate_with and p not in can_visualize]

    nav_options = get_nav_options(request)

    return render(request, 'project/projects.html',
                  {'public_projects': public_projects,
                   'user_projects': user_projects,
                   'collaborate_with': collaborate_with,
                   'can_visualize': can_visualize,
                   'nav_options': nav_options})




@login_required(login_url='account/login')
def delete_objs(request, project_id):
    user = request.user
    project = get_project(project_id)

    if can_delete(project, user):
        if request.method == 'POST':
            del_confirm = request.POST.get("submit")
            obj_type = request.POST.get("object")
            deleted = False

            # requires confirmation to delete objs
            if del_confirm == "delete":
                objs_to_del = get_objs_by_type(
                    obj_type, request.POST.getlist("selected"))

                for obj in objs_to_del:
                    obj.hide()

                deleted = True

            return redirect(
                "%s?deleted=%s" % (
                    reverse("project:manage-%ss" % obj_type, args=(project_id,)),
                    deleted))

    return not_allowed_page(request)


@login_required(login_url='/account/login')
def check_deletion(request, project_id):
    """View that receives from a form a list of objects to delete
    and asks the user to confirm deletion"""

    user = request.user
    project = get_project(project_id)
    content = {}
    content.update(csrf(request))
    content["project"] = project
    content["nav_options"] = get_nav_options(request)

    if can_delete(project, user):
        if request.method == 'POST':
            obj_type = request.POST.get("object").lower()
            selected_objs = request.POST.getlist("selected")
            # didn't select any object
            if len(selected_objs) == 0:
                return redirect(
                    "%s?deleted=0" %
                    reverse("project:manage-%ss" % obj_type,
                            args=(project_id,)))

            content["objs"] = get_objs_by_type(
                obj_type, selected_objs)

            return render(request, "project/check-deletion.html",
                          content)

    return not_allowed_page(request)


@login_required(login_url='/account/login')
def create_project(request):

    nav_options = get_nav_options(request)

    if request.method == 'POST':

        user = request.user
        form = ProjectForm(user=user, data=request.POST)

        if form.is_valid():
            project = form.save()
            viewers_group = project.create_viewers_group()
            collaborators_group = project.create_collaborators_group()

            # set groups permissions
            project.set_permissions(viewers_group)
            project.set_permissions(collaborators_group)

            return redirect('/project/%d' % project.ID)
    else:
        form = ProjectForm()

    return render(request, 'project/create-project.html',
                  {'form': form,
                   'nav_options': nav_options})


@login_required(login_url='/account/login')
def edit_project(request, project_id):

    nav_options = get_nav_options(request)

    user = request.user

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
        raise Http404

    except Exception, e:
        return HttpResponse("Error: %s please contact administration" % str(e))

    else:
        if can_change(project, user):
            if request.method == 'POST':
                # different edition for owner and collaborators
                if project.is_owner(user):
                    form = OwnersEditProjectForm(
                        data=request.POST, instance=project)
                else:
                    form = EditProjectForm(data=request.POST, instance=project)

                if form.is_valid():
                    form.save()
                    return render(
                        request, 'project/edit-project.html',
                        {'nav_options': nav_options,
                         'changed': True,
                         'form': form,
                         'project': project})
            else:
                # different edition for owner and collaborators
                if project.is_owner(user):
                    form = OwnersEditProjectForm(instance=project)
                else:
                    form = EditProjectForm(instance=project)

            return render(
                request, 'project/edit-project.html',
                {'nav_options': nav_options,
                 'form': form,
                 'project': project})

        else:
            return not_allowed_page(request)


@login_required(login_url="/account/login")
def add_manufacturer(request, project_id):
    user = request.user
    nav_options = get_nav_options(request)
    istherenew_make = None

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
                raise Http404

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
                request, "project/create-manufacturer.html",
                {"nav_options": nav_options,
                 "manufacturer_form": manufacturer_form,
                 "transmitter_form": transmitter_form,
                 "changed": istherenew_make,
                 "project": project})
        else:
            return not_allowed_page(request)


@login_required(login_url="account/login")
def add_location(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddLocationForm(data=request.POST),
        get_form=AddLocationForm(),
        template_path="project/create-location.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-locations", args=(project_id,)))


@login_required(login_url="/account/login")
def add_transmitter(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddTransmitterForm(data=request.POST),
        get_form=AddTransmitterForm(),
        template_path="project/create-transmitter.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-transmitters", args=(project_id,)))


@login_required(login_url="/account/login")
def add_target(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddTargetForm(data=request.POST),
        get_form=AddTargetForm(),
        template_path="project/create-target.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-targets", args=(project_id,))
        )


@login_required(login_url="/account/login")
def add_deployment(request, project_id):
    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=AddDeploymentForm(data=request.POST),
        get_form=AddDeploymentForm(),
        template_path="project/create-deployment.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-deployments", args=(project_id,))
        )


def show_project(request, project_id):

    nav_options = get_nav_options(request)
    user = request.user

    try:
        project = Project.objects.get(ID=project_id)
        if project.is_public:
            return render(
                request, 'project/display-project.html',
                {'project': project,
                 'nav_options': nav_options})

        else:
            if project.is_owner(user)\
                    or ((project.is_collaborator(user)
                        or project.is_viewer(user))
                        and user.has_perm("project.can_view")):
                    return render(
                        request,
                        'project/display-project.html',
                        {'project': project,
                         'nav_options': nav_options})

            else:
                return not_allowed_page(request)

    except ObjectDoesNotExist:
        raise Http404



@login_required(login_url="/account/login")
def manage_targets(request, project_id):

    project = get_project(project_id)
    content = {}
    content["nav_options"] = get_nav_options(request)
    content["project"] = project
    content["objects"] = project.get_targets()
    content["obj_type"] = "target"
    content["foreign_fields"] = []
    content["excluded_fields"] = ["projectID", "ID", "is_hidden"]

    return render_manage_page(
        request,
        project,
        "project/manage_targets.html",
        content)


@login_required(login_url="/account/login")
def manage_locations(request, project_id):

    project = get_project(project_id)
    context = Context() 
    context["nav_options"] = get_nav_options(request)
    context["project"] = project
    context["objects"] = project.get_locations()
    context["obj_type"] = "location"
    context["foreign_fields"] = []
    context["excluded_fields"] = ["projectID", "ID", "is_hidden"]

    return render_manage_page(
        request,
        project,
        "project/manage_locations.html",
        context)


@login_required(login_url="/account/login")
def manage_transmitters(request, project_id):

    project = get_project(project_id)
    content = {}
    content["nav_options"] = get_nav_options(request)
    content["project"] = project
    content["objects"] = project.get_transmitters()
    content["obj_type"] = "transmitter"
    content["foreign_fields"] = ["tx_makeID"]
    content["excluded_fields"] = ["projectID", "ID", "is_hidden"]

    return render_manage_page(
        request,
        project,
        "project/manage_transmitters.html",
        content)


@login_required(login_url="/account/login")
def manage_deployments(request, project_id):

    project = get_project(project_id)
    content = {}
    content["nav_options"] = get_nav_options(request)
    content["project"] = project
    content["objects"] = project.get_deployments()
    content["obj_type"] = "deployment"
    content["foreign_fields"] = ["txID", "targetID"]
    content["excluded_fields"] = [
        "projectID", "ID", "is_hidden", "tx_makeID", "serial_no"]

    return render_manage_page(
        request,
        project,
        "project/manage_deployments.html",
        content)


@login_required(login_url="/account/login")
def edit_transmitter(request, project_id, transmitter_id):
    query = get_query("transmitter")
    transmitter = query(transmitter_id)

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditTransmitterForm(data=request.POST, instance=transmitter),
        get_form=EditTransmitterForm(instance=transmitter),
        template_path="project/edit-transmitter.html",
        success_url="%s?new_element=True" % reverse(
            "project:edit-transmitter", args=(project_id, transmitter_id)))


@login_required(login_url="/account/login")
def edit_target(request, project_id, target_id):
    query = get_query("target")
    target = query(target_id)

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditTargetForm(data=request.POST, instance=target),
        get_form=EditTargetForm(instance=target),
        template_path="project/edit-target.html",
        success_url="%s?new_element=True" % reverse(
            "project:edit-target", args=(project_id, target_id)))


@login_required(login_url="/account/login")
def edit_location(request, project_id, location_id):
    query = get_query("location")
    location = query(location_id)

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditLocationForm(data=request.POST, instance=location),
        get_form=EditLocationForm(instance=location),
        template_path="project/edit-location.html",
        success_url="%s?new_element=True" % reverse(
            "project:edit-location", args=(project_id, location_id)))


@login_required(login_url="/account/login")
def edit_deployment(request, project_id, deployment_id):
    query = get_query("deployment")
    deployment = query(deployment_id)

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditDeploymentForm(data=request.POST, instance=deployment),
        get_form=EditDeploymentForm(
            instance=deployment,
            initial={'time_start':
                     utils.strfdate(
                         utils.timestamp_todate(deployment.time_start))}),
        template_path="project/edit-deployment.html",
        success_url="%s?new_element=True" % reverse(
            "project:edit-deployment", args=(project_id, deployment_id)))



def render_data(request):
    """Renders a JSON serialized data
       By now only admins have access to this"""

    user = request.user

    try:
        data = rest_api.get_model_data(request)
        data = rest_api.json_parse(data)

        if user.is_superuser:
            return HttpResponse(
                json.dumps(data, cls=utils.DateTimeEncoder),
                content_type="application/json")
        else:
            return not_allowed_page(request)

    except Exception, e:
        print e
        return HttpResponseBadRequest("Object not found")
        
