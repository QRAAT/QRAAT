import json
import utils
import rest_api
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
from project.models import Project, Tx, TxMake, TxMakeParameters, Location, Target, Deployment
#from project.models import Site, Telemetry, Est
from django.forms import modelformset_factory
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
    print "in views.index"
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
    print "in views.projects"
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


# Returns json format of new {ID:txMake.ID,manufacturer:manufacturer,model:model}, or false 
@login_required(login_url="/account/login")
def add_manufacturer_inline(request, project_id):
    user = request.user
    nav_options = get_nav_options(request)
    istherenew_make = None
    successful = False

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
                raise Http404

    else:
        if can_change(project, user):
            if request.method == 'POST':
                # Saving the tx make/model
                form = dict(request.POST)
                # Each key should have only one none null value (unless people mess with the html?)
                # vals should be non empty, from in-browser validation
                for val in form['manufacturer']:
                    if val:
                        manufacturer = val
                        break
                for val in form['model']:
                    if val:
                        model = val
                        break
                for val in form['pulse_width']:
                    if val:
                        pulse_width = val
                        break
                for val in form['pulse_rate']:
                    if val:
                        pulse_rate = val
                        break
                txMake = TxMake(manufacturer=manufacturer, model=model, demod_type=form['demod_type'][0])
                
                txMake.save()
                if(form['demod_type'][0]==u'pulse'): 
                    TxMakeParameters(tx_makeID=txMake, name='pulse_width', value=pulse_width).save()
                    TxMakeParameters(tx_makeID=txMake, name='pulse_rate', value=pulse_rate).save()
                    # Hardcoded
                    TxMakeParameters(tx_makeID=txMake, name='band3', value=150).save()
                    TxMakeParameters(tx_makeID=txMake, name='band10', value=900).save()
                # Const demod_type doesn't store any parameters
                return HttpResponse(json.dumps({'ID':txMake.ID,'manufacturer':manufacturer,'model':model}), content_type="application/json")
            elif request.method == 'GET':
                return HttpResponse(json.dumps({'result':False}), content_type="application/json")

def add_target_inline(request, project_id):
    user = request.user
    nav_options = get_nav_options(request)
    istherenew_make = None
    successful = False

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
                raise Http404

    else:
        if can_change(project, user):
            if request.method == 'POST':
                form = dict(request.POST)
                # Each key should have only one none null value (unless people mess with the html?)
                # vals should be non empty, from in-browser validation
                for val in form['name']:
                    if val:
                        name = val
                        break
                for val in form['description']:
                    if val:
                        description = val
                        break
                for val in form['max_speed_family']:
                    if val:
                        max_speed_family = val
                        break
                for val in form['speed_burst']:
                    if val:
                        speed_burst = val
                        break
                for val in form['speed_sustained']:
                    if val:
                        speed_sustained = val
                        break
                for val in form['speed_limit']:
                    if val:
                        speed_limit = val
                        break
                
                target = Target(name=name, description=description, max_speed_family=max_speed_family, speed_burst=speed_burst, speed_sustained=speed_sustained, speed_limit=speed_limit, projectID=Project.objects.get(pk=project_id))
                target.save()
                return HttpResponse(json.dumps({'ID':target.ID,'name':target.name}), content_type="application/json")
            elif request.method == 'GET':
                return HttpResponse(json.dumps({'result':False}), content_type="application/json")
                 
# Returns json format of new {}, or false 
@login_required(login_url="/account/login")
def add_target_inline(request, project_id):
    user = request.user
    nav_options = get_nav_options(request)
    istherenew_make = None
    successful = False

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
                raise Http404

    else:
        if can_change(project, user):
            if request.method == 'POST':
                # Saving the target
                form = dict(request.POST)
                # Each key should have only one none null value (unless people mess with the html?)
                # vals should be non empty, from in-browser validation
                for val in form['name']:
                    if val:
                        name = val
                        break
                for val in form['description']:
                    if val:
                        description = val
                        break
                for val in form['max_speed_family']:
                    if val:
                        max_speed_family = val
                        break
                for val in form['speed_burst']:
                    if val:
                        speed_burst = val
                        break
                for val in form['speed_sustained']:
                    if val:
                        speed_sustained = val
                        break
                for val in form['speed_limit']:
                    if val:
                        speed_limit = val
                        break
                
                target = Target(name=name, description=description, max_speed_family=max_speed_family, speed_burst=speed_burst, speed_sustained=speed_sustained, speed_limit=speed_limit,projectID=project)
                target.save()
                return HttpResponse(json.dumps({'ID':target.ID,'name':name}), content_type="application/json")
            elif request.method == 'GET':
                return HttpResponse(json.dumps({'result':False}), content_type="application/json")
                 
@login_required(login_url="account/login")
def create_placeholder_target(request, project_id):
    user = request.user 
    nav_options = get_nav_options(request)
    istherenew_make = None
    successful = False

    try:
        project = Project.objects.get(ID=project_id)

    except ObjectDoesNotExist:
                raise Http404

    else:
        if can_change(project, user):
            if request.method == 'POST':
                form = dict(request.POST)
                ntargets = int(form['number'][0])
                copyID = int(form['copyID'][0])
                try:
                    copyTarget = Target.objects.get(ID=copyID)
                except ObjectDoesNotExist:
                    raise Http404
                else:
                    ids = []
                    names = []
                    for i in range(0,ntargets):
                        # if pk = None, django generates the primary key for us, inserts as new row
                        copyTarget.pk = None
                        copyTarget.name = Placeholder + " " + str(i)
                        copyTarget.save()
                        ids.append(copyTarget.ID)
                        names.append(copyTarget.name)
                    name = "assbut"
                    return HttpResponse(json.dumps({'names':names, 'ids':ids}), content_type="application/json")
            elif request.method == 'GET':
                raise PermissionDenied
                return HttpResponse(json.dumps({'result':False}), content_type="application/json")


@login_required(login_url="account/login")
def add_location(request, project_id):
    return render_project_formset(
        request=request,
        project_id=project_id,
        post_formset=modelformset_factory(Location, form=AddLocationForm)(data=request.POST),
        get_formset=modelformset_factory(Location, form=AddLocationForm, extra=2)(queryset=Location.objects.none()),
        template_path="project/create-location.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-locations", args=(project_id,)))


@login_required(login_url="/account/login")
def add_transmitter(request, project_id):
    return render_project_formset(
        request=request,
        project_id=project_id,
        post_formset=modelformset_factory(Tx, form=AddTransmitterForm)(data=request.POST),
        get_formset=modelformset_factory(Tx, form=AddTransmitterForm, extra=2)(queryset=Tx.objects.none()),
        template_path="project/create-transmitter.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-transmitters", args=(project_id,)))


@login_required(login_url="/account/login")
def add_target(request, project_id):
    return render_project_formset(
        request=request,
        project_id=project_id,
        post_formset=modelformset_factory(Target, form=AddTargetForm)(data=request.POST),
        get_formset=modelformset_factory(Target, form=AddTargetForm, extra=2)(queryset=Target.objects.none()),
        template_path="project/create-target.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-targets", args=(project_id,))
        )


@login_required(login_url="/account/login")
def add_deployment(request, project_id):
    return render_project_formset(
        request=request,
        project_id=project_id,
        post_formset=modelformset_factory(Deployment, form=AddDeploymentForm)(data=request.POST),
        get_formset=modelformset_factory(Deployment, form=AddDeploymentForm, extra=2)(queryset=Deployment.objects.none()),
        template_path="project/create-deployment.html",
        success_url="%s?new_element=True" % reverse(
            "project:manage-deployments", args=(project_id,))
        )

"""
This is a somewhat lengthy function that deals with displaying multiple forms in succession on one URL page.
It starts off on a simple page where you select the number of form rows, beyond that it gets complicated.

request.method == 'POST'
These requests are from submitting the forms (besides the initial simple 'number' form). 
We pass the request to render_project_formset (with redirect_bool=False), which validates the form, and we store the return value in 'rval'. 
If the form is valid, then b/c redirect_bool==False, it does not return a HttpResponse, but instead the model objects built created by the form. 
If the form is not valid, then it returns a rendered page (HttpResponse) with the form errors included.
We check what type the return value is, and if it's type HttpResonse, then the form was not valid and this function returns the HttpResponse returned by render_project_formset.
If it's not, then we call and return render_project_formset with the modelform of the next form, or redirect to some page if it's the last form.
"""
# The worst function ever
@login_required(login_url="/account/login")
def bulk_wizard(request, project_id, number=0):
    user = request.user
    try:
        project = Project.objects.get(ID=project_id)
        if project.is_owner(user) or project.is_collaborator(user):
            pass # Just to take the rest of the function out of this block
        else:
            return not_allowed_page(request)

    except ObjectDoesNotExist:
        raise Http404

    # GET requests are from non submission page loads. 
    if request.method == 'GET':
        # Check how many never before used tx and targets there are for this project
        # QuerySets
        # Tx and Target ID's that've been used
        usedTxs = []
        usedTargets = []
        for d in project.get_deployments():
            usedTxs.append(d.txID.ID)
            usedTargets.append(d.targetID.ID)
        pTx = project.get_transmitters().exclude(pk__in=usedTxs)
        pTarget = project.get_targets().exclude(pk__in=usedTargets)
        pTxIDs = [x.pk for x in pTx]
        pTargetIDs = [x.pk for x in pTarget]

        num = request.GET.get("number")
        # Check number of forms present
        if not num is None: 
            try:
                num = int(num)
                if num < 1:
                    return HttpResponseBadRequest("Non positive value")
            except ValueError:
                return HttpResponseBadRequest("Entered a non-number")

        txIDs = request.GET.get("txIDs")
        targetIDs = request.GET.get("targetIDs")

        # Check if using existing targets
        existing_tx = request.GET.get("existing_tx")
        existing_tx_target = request.GET.get("existing_tx_target")
        if existing_tx == "true":
            if not num:
                return render_bulk_page(
                    request,
                    project,
                    "project/bulk-create.html",
                    extra_context={"readonlyformset": modelformset_factory(Tx, form=AddTransmitterForm, extra=0)(queryset=pTx),
                        "unused_tx_num": len(pTxIDs), 
                        "unused_target_num": len(pTargetIDs),
                        "current_form": "tx",
                        "txIDs": " ".join(str(__) for __ in pTxIDs)}
                )
            else:
                return render_wizard_project_formset(
                    request=request,
                    project_id=project_id,
                    post_formset=modelformset_factory(Target, form=AddTargetForm)(),#(data=request.POST),
                    get_formset=modelformset_factory(Target, form=AddTargetForm, extra=num)(queryset=Target.objects.none()),
                    template_path="project/bulk-create.html",
                    success_url="",
                    redirect_bool=False,
                    extra_context={"title_msg": "New Target",
                                    "current_form": "target",}
                ) 

        elif existing_tx_target == "tx":
            return render_bulk_page(
                request,
                project,
                "project/bulk-create.html",
                extra_context={"readonlyformset": modelformset_factory(Tx, form=AddTransmitterForm, extra=0)(queryset=pTx),
                    "unused_tx_num": len(pTxIDs), 
                    "unused_target_num": len(pTargetIDs),
                    "current_form": "tx",
                }
            )
        elif existing_tx_target == "target":
            if not num:
                return render_bulk_page(
                    request,
                    project,
                    "project/bulk-create.html",
                    extra_context={"readonlyformset": modelformset_factory(Target, form=AddTargetForm, extra=0)(queryset=pTarget),
                        "unused_tx_num": len(pTxIDs), 
                        "unused_target_num": len(pTargetIDs),
                        "current_form": "target",
                        "targetIDs": " ".join(str(__) for __ in pTargetIDs)}
                    )
            else:
                return render_wizard_project_formset(
                    request=request,
                    project_id=project_id,
                    post_formset=modelformset_factory(Deployment, form=AddDeploymentForm)(data=request.POST),
                    get_formset=modelformset_factory(Deployment, form=AddDeploymentForm, extra=num)(queryset=Deployment.objects.none()),
                    template_path="project/bulk-create.html",
                    success_url="",
                    redirect_bool=False,
                    extra_context={"current_form": "deployment",
                        "txIDs": " ".join(str(__) for __ in pTxIDs),
                        "targetIDs": " ".join(str(__) for __ in pTargetIDs)}
                ) 
        # If no num 
        if num is None or num == '':
            return render_bulk_page(
                request,
                project,
                "project/bulk-create.html",
                extra_context={"unused_tx_num": len(pTx), "unused_target_num": len(pTarget)}
                )


        # Tx error
        if request.GET.get("form-0-serial_no"): #elif request.GET.get("form-0-tx_makeID") != None:
            return render_wizard_project_formset(
                request=request,
                project_id=project_id,
                post_formset=modelformset_factory(Tx, form=AddTransmitterForm)(data=request.POST),
                get_formset=modelformset_factory(Tx, form=AddTransmitterForm, extra=num)(queryset=Tx.objects.none()),
                template_path="project/bulk-create.html",
                success_url="",
                redirect_bool=False,
                extra_context={"title_msg":"New Transmitter", "current_form": "tx"}
                )
        # Target error
        elif request.GET.get("form-0-name") != None: # Tx doesn't have a name field
            return render_wizard_project_formset(
                request=request,
                project_id=project_id,
                post_formset=modelformset_factory(Target, form=AddTargetForm)(data=request.POST),
                get_formset=modelformset_factory(Target, form=AddTargetForm, extra=num)(queryset=Target.objects.none()),
                template_path="project/bulk-create.html",
                success_url="",
                redirect_bool=False,
                extra_context={"title_msg": "New Target", "current_form": "target", "txIDs": txIDs}
                )
        # Dep error     
        elif request.GET.get("form-0-targetID") != None:
            print "error dep"
            return render_wizard_project_formset(
                request=request,
                project_id=project_id,
                post_formset=modelformset_factory(Deployment, form=AddDeploymentForm)(data=request.POST),
                get_formset=modelformset_factory(Deployment, form=AddDeploymentForm, extra=num)(queryset=Deployment.objects.none()),
                template_path="project/bulk-create.html",
                success_url="",
                redirect_bool=False,
                extra_context={"title_msg": "New Deployment","current_form": "deployment", "txIDs": txIDs, "targetIDs": targetIDs}
                )
        # From initial page that selects the num
        # Tx, not error
        else:
            return render_wizard_project_formset(
                request=request,
                project_id=project_id,
                post_formset=modelformset_factory(Tx, form=AddTransmitterForm)(data=request.POST),
                get_formset=modelformset_factory(Tx, form=AddTransmitterForm, extra=num)(queryset=Tx.objects.none()),
                template_path="project/bulk-create.html",
                success_url="",
                redirect_bool=False,
                extra_context={"title_msg":"New Transmitter", "current_form": "tx"}
                )
        
        
    # POST requests from submitting forms
    elif request.method == 'POST':
        num = request.GET.get("number")

        txIDs = request.POST.get("txIDs")
        targetIDs = request.POST.get("targetIDs")
        try:
            num = int(num)
            if num < 1:
                return HttpResponseBadRequest("Entered a non positive value")
        except ValueError:
            return HttpResponseBadRequest("Entered a non-number")
            
        # If Tx
        if request.POST.get("form-0-tx_makeID") != None:
            rval = render_wizard_project_formset(
                    request=request,
                    project_id=project_id,
                    post_formset=modelformset_factory(Tx, form=AddTransmitterForm)(data=request.POST),
                    get_formset=modelformset_factory(Tx, form=AddTransmitterForm, extra=num)(queryset=Tx.objects.none()),
                    template_path="project/bulk-create.html",
                    success_url="",
                    redirect_bool=False,
                    extra_context={"title_msg":"New Transmitter", "current_form": "tx"}
                    ) 
        # If Deployment
        elif request.POST.get("form-0-targetID") != None:
            #request.method = 'GET' # Dumb way to make request GET
            rval = render_wizard_project_formset(
                request=request,
                project_id=project_id,
                post_formset=modelformset_factory(Deployment, form=AddDeploymentForm)(data=request.POST),
                get_formset=modelformset_factory(Deployment, form=AddDeploymentForm, extra=num)(queryset=Deployment.objects.none()),
                template_path="project/bulk-create.html",
                success_url="",
                redirect_bool=False,
                extra_context={"title_msg": "New Deployment","current_form": "deployment", "txIDs": txIDs, "targetIDs": targetIDs}
            ) 
        # If Target
        elif request.POST.get("form-0-name") != None:
            #request.method = 'GET' # Dumb way to make request GET
            rval = render_wizard_project_formset(
                request=request,
                project_id=project_id,
                post_formset=modelformset_factory(Target, form=AddTargetForm)(data=request.POST),
                get_formset=modelformset_factory(Target, form=AddTargetForm, extra=num)(queryset=Target.objects.none()),
                template_path="project/bulk-create.html",
                success_url="",
                redirect_bool=False,
                extra_context={"title_msg": "New Target", "current_form": "target", "txIDs": txIDs}
            ) 
            
        # Now we check what render_wizard_project_formset returns. Because we used "redirect_bool=False", when the form is valid and we would usually be redirected to another page, we instead return the saved objects, not HttpResponse. 
        # Thus, if not instance of HttpResonse, there was a valid form submission
        if not isinstance(rval, HttpResponse):
            # For when forms were successfully validated. Instead of redirecting to another page, just come back to this page with new formset
            # Shoddy way of testing which model form we're on. Perhaps turn the keys of request.POST into list, search for field ending in tx_makeID
            # Submitted valid Tx form, return a Target form
            if request.POST.get("form-0-tx_makeID") != None:
                request.method = 'GET' # Dumb way to make request GET
                ids = " ".join(str(x.pk) for x in rval)
                return render_wizard_project_formset(
                    request=request,
                    project_id=project_id,
                    post_formset=modelformset_factory(Target, form=AddTargetForm)(),#(data=request.POST),
                    get_formset=modelformset_factory(Target, form=AddTargetForm, extra=num)(queryset=Target.objects.none()),
                    template_path="project/bulk-create.html",
                    success_url="",
                    redirect_bool=False,
                    extra_context={"title_msg": "New Target",
                                    "current_form": "target",
                                    "txIDs": ids}
                ) 
            # Deployment. Valid deployment form submission, so we're done with the wizard, so we just go to the manage deployment page.
            elif request.POST.get("form-0-targetID") != None:
                #request.method = 'GET' # Dumb way to make request GET
                success_url="%s?new_element=True" % reverse(
                    "project:manage-deployments", args=(project_id,))
                return redirect(success_url)
            # Target to Dep
            elif request.POST.get("form-0-name") != None:
                request.method = 'GET' # Dumb way to make request GET
                ids = " ".join(str(x.pk) for x in rval)
                return render_wizard_project_formset(
                    request=request,
                    project_id=project_id,
                    post_formset=modelformset_factory(Deployment, form=AddDeploymentForm)(),#(data=request.POST),
                    get_formset=modelformset_factory(Deployment, form=AddDeploymentForm, extra=num)(queryset=Deployment.objects.none()),
                    template_path="project/bulk-create.html",
                    success_url="",
                    redirect_bool=False,
                    extra_context={"title_msg": "New Deployment",
                                    "current_form": "deployment",
                                    "txIDs": txIDs,
                                    "targetIDs": ids}
                ) 
        else:
            return rval     

def show_project(request, project_id):

    nav_options = get_nav_options(request)
    user = request.user
    try:
        project = Project.objects.get(ID=project_id)
        have_started_deployments = len(project.get_deployments().filter(time_start__lte = time.time())) != 0
        print have_started_deployments

        if project.is_public:
            return render(
                request, 'project/display-project.html',
                {'project': project,
                 'nav_options': nav_options,
                 'have_started_deps': have_started_deployments})

        else:
            if project.is_owner(user)\
                    or ((project.is_collaborator(user)
                        or project.is_viewer(user))
                        and user.has_perm("project.can_view")):
                    return render(
                        request,
                        'project/display-project.html',
                        {'project': project,
                         'nav_options': nav_options,
                         'have_started_deps': have_started_deployments})

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
    context = {} # Context() created a problem (no csrf token) in Django 1.8
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

    if isinstance( deployment.time_end, (int, long) ):
        time_end = utils.strftime(utils.timestamp_todate(deployment.time_end))
    else:
        time_end = "None"

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditDeploymentForm(data=request.POST, instance=deployment),
        get_form=EditDeploymentForm(
            instance=deployment,
            initial={'time_start':
                     utils.strftime(
                         utils.timestamp_todate(deployment.time_start)),
                     'time_end': time_end}),
        template_path="project/edit-deployment.html",
        success_url="%s?new_element=True" % reverse(
            "project:edit-deployment", args=(project_id, deployment_id)))

@login_required(login_url="/account/login")
def movebank_export(request, project_id):
    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        query = get_query("transmitter")
        tx = query(transmitter_id)
        return HttpResponse(
            "Transmitter: %d Model: %s Manufacturer: %s" % (
                tx.ID, tx.tx_makeID.model, tx.tx_makeID.manufacturer))
    else:
        pass

def about(request):
    nav_options = get_nav_options(request)
    return render(request, "about.html",{'nav_options': nav_options},
    )

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
        
