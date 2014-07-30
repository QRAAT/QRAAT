from django.db.models import Q
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from models import Project, Tx, Location
from models import Target, Deployment
from forms import ProjectForm, EditProjectForm, AddTransmitterForm
from forms import AddManufacturerForm, AddTargetForm
from forms import AddDeploymentForm, AddLocationForm
from forms import EditTargetForm, EditTransmitterForm


def not_allowed_page(request):
    return HttpResponse("Action not allowed")


def get_query(obj_type):
    """ Receives an object type and return it's specific
    query"""

    query = None
    obj_type = obj_type.lower()

    try:
        #  switch query based on obj type
        if(obj_type == "transmitter"):
            query = lambda obj_id: Tx.objects.get(ID=obj_id)
        elif(obj_type == "target"):
            query = lambda obj_id: Target.objects.get(ID=obj_id)
        elif(obj_type == "location"):
            query = lambda obj_id: Location.objects.get(ID=obj_id)
        elif(obj_type == "deployment"):
            query = lambda obj_id: Deployment.objects.get(ID=obj_id)
    except ObjectDoesNotExist:
        raise ObjectDoesNotExist
    else:
        if not query:
            raise ObjectDoesNotExist

        return query


def get_objs_by_type(obj_type, obj_ids):
    """Receives an object type and a list of ids and return a list of
    Objects based in it's type i.e transmitter, location, target, or
    deployment"""

    try:
        query = get_query(obj_type)
        #  maps items selected on the form in a list of objects
        objs = map(query, obj_ids)
    except Exception, e:
        raise e

    else:
        return objs


def can_delete(project, user):
    """A user can delete content in a project if the user is the project owner or
    if the user is in the collaborators group and the group has permission
    to delete content on the project"""

    # With has_perm we can have different permissions for group
    return project.is_owner(user) or\
        (project.is_collaborator(user) and
            user.has_perm("qraatview.can_delete"))


def can_change(project, user):
    """A user can change content in a project if the user is the project owner or
    if the user is in the collaborators group and the group has permission
    to change content on the project"""

    return project.is_owner(user) or\
        (project.is_collaborator(user)
            and user.has_perm("qraatview.can_change"))


def can_view(project, user):
    """Users can view content in a project if the project is public,
    or the user is the project owner, or the user is a project collaborator
    or the user is a project viewer"""

    return project.is_public\
        or project.is_owner(user)\
        or (project.is_collaborator(user) and user.has_perm("view"))\
        or (project.is_viewer(user) and user.has_perm("view"))


def index(request):
    nav_options = get_nav_options(request)
    user = request.user

    if user.is_authenticated():
        return projects(request)
    else:
        public_projects = Project.objects.filter(
            is_public=True, is_hidden=False)

        return render(
            request, "qraat_site/index.html",
            {'nav_options': nav_options,
             'projects': public_projects})


def get_project(project_id):
    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
        return HttpResponse("We didn't find this project")
    else:
        return project


def show_transmitter(request, project_id, transmitter_id):
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


def show_target(request, project_id, target_id):

    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        query = get_query("target")
        target = query(target_id)
        return HttpResponse(target)
    else:
        return not_allowed_page(request)


def show_location(request, project_id, location_id):
    user = request.user
    project = get_project(project_id)

    if can_view(project, user):
        query = get_query("location")
        location = query(location_id)

        return HttpResponse(
            "Location: %s location: %s" % (location.name, location.location))
    else:
        return not_allowed_page(request)


@login_required(login_url='/auth/login')
def projects(request):
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

    return render(request, 'qraat_site/projects.html',
                  {'public_projects': public_projects,
                   'user_projects': user_projects,
                   'collaborate_with': collaborate_with,
                   'can_visualize': can_visualize,
                   'nav_options': nav_options})


def render_project_form(
        request, project_id, post_form,
        get_form, template_path, success_url):

    user = request.user
    project = get_project(project_id)
    nav_options = get_nav_options(request)
    thereis_newelement = None

    if can_change(project, user):
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
        return not_allowed_page(request)


def render_manage_page(request, project, template_path, content):
    user = request.user

    if request.method == "GET":
        content["changed"] = request.GET.get("new_element")
        content["deleted"] = request.GET.get("deleted")

    if can_change(project, user):

        return render(
            request, template_path,
            content)
    else:
        return not_allowed_page(request)


@login_required(login_url='auth/login')
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
                    reverse("qraat:manage-%ss" % obj_type, args=project_id),
                    deleted))

    return not_allowed_page(request)


@login_required(login_url='/auth/login')
def check_deletion(request, project_id):
    user = request.user
    project = get_project(project_id)
    content = {}
    content.update(csrf(request))
    content["project"] = project
    content["nav_options"] = get_nav_options(request)

    if can_delete(project, user):
        if request.method == 'POST':
            obj_type = request.POST.get("object").lower()
            content["objs"] = get_objs_by_type(
                obj_type, request.POST.getlist("selected"))

            # didn't select any object
            if len(content["objs"]) == 0:
                return redirect("%s?deleted=0" %
                    reverse("qraat:manage-%ss" % obj_type,
                            args=(project_id,)))

            return render(request, "qraat_site/check-deletion.html",
                          content)

    return not_allowed_page(request)


@login_required(login_url='/auth/login')
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

    except Exception, e:
        return HttpResponse("Error: %s please contact administration" % str(e))

    else:
        if project.is_owner(user)\
                or (project.is_collaborator(user)
                    and user.has_perm("qraatview.can_change")):
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
            return not_allowed_page(request)


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
            return not_allowed_page(request)


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
        success_url="%s?new_element=True" % reverse(
            "qraat:manage-transmitters", args=(project_id,)))


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
            if project.is_owner(user)\
                    or ((project.is_collaborator(user)
                        or project.is_viewer(user))
                        and user.has_perm("qraatview.can_view")):

                    return render(
                        request,
                        'qraat_site/display-project.html',
                        {'project': project,
                         'nav_options': nav_options})

            else:
                return not_allowed_page(request)

    except ObjectDoesNotExist:
        return HttpResponse("Project not found")


@login_required(login_url="/auth/login")
def manage_targets(request, project_id):

    project = get_project(project_id)
    content = {}
    content["nav_options"] = get_nav_options(request)
    content["project"] = project
    content["objects"] = project.get_targets()

    return render_manage_page(
        request,
        project,
        "qraat_site/manage_targets.html",
        content)


@login_required(login_url="/auth/login")
def manage_locations(request, project_id):
    return HttpResponse("Not implemented yet")


@login_required(login_url="/auth/login")
def manage_transmitters(request, project_id):

    project = get_project(project_id)
    content = {}
    content["nav_options"] = get_nav_options(request)
    content["project"] = project
    content["objects"] = project.get_transmitters()

    return render_manage_page(
        request,
        project,
        "qraat_site/manage_transmitters.html",
        content)


@login_required(login_url="/auth/login")
def edit_transmitter(request, project_id, transmitter_id):
    query = get_query("transmitter")
    transmitter = query(transmitter_id)

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditTransmitterForm(data=request.POST, instance=transmitter),
        get_form=EditTransmitterForm(instance=transmitter),
        template_path="qraat_site/edit-transmitter.html",
        success_url="%s?new_element=True" % reverse(
            "qraat:edit-transmitter", args=(project_id, transmitter_id)))


@login_required(login_url="/auth/login")
def edit_target(request, project_id, target_id):
    query = get_query("target")
    target = query(target_id)

    return render_project_form(
        request=request,
        project_id=project_id,
        post_form=EditTargetForm(data=request.POST, instance=target),
        get_form=EditTargetForm(instance=target),
        template_path="qraat_site/edit-target.html",
        success_url="%s?new_element=True" % reverse(
            "qraat:edit-target", args=(project_id, target_id)))


@login_required(login_url="/auth/login")
def manage_deployments(request, project_id):
    return HttpResponse("Not implemented yet")


def get_nav_options(request):
    nav_options = []
    user = request.user

    if user.is_authenticated():
        nav_options.append({"url": "qraat:projects",
                            "name": "Projects"})

        if user.is_superuser:
            super_user_opts = [
                {"url": "auth:users",
                 "name": "Users"},
                {"url": "admin:index",
                 "name": "Admin Pages"}]

            for opt in super_user_opts:  # Add admin options
                nav_options.append(opt)
    return nav_options
