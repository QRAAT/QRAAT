from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import render, redirect
from project.models import Project, Tx, Target, Location, Deployment

def not_allowed_page(request):
    """This view renders a page for forbidden action
    with HTTP 403 status and a message"""
    if request.user.is_authenticated():
        raise PermissionDenied #403
    else:
        return redirect("/account/login/?next=%s" % request.get_full_path()) #redirect user to login page to see if they have access permission


def get_query(obj_type):
    """ This function selects a query based in a model verbose name

    :param obj_type: Object's verbose name
    :type obj_type: str.
    :returns:  func -- A function to query a model by id

    .. note::

       .. code-block:: python

          #Example of usage:
          query = get_query("transmitters")
          transmitter_10 = query(10)
    """

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
        else:
            raise ObjectDoesNotExist

    except ObjectDoesNotExist:
        raise ObjectDoesNotExist
    else:
        return query


def get_objs_by_type(obj_type, obj_ids):
    """Receives an object type and a list of ids and return a list of
    Objects based in it's type i.e transmitter, location, target, or
    deployment

    :param obj_type: Model's verbose name
    :type obj_type: str.
    :returns:  list -- list of models for each given id
    :raises: ObjectDoesNotExist
    """

    query = get_query(obj_type)

    #  maps items selected on the form in a list of objects
    objs = map(query, obj_ids)

    return objs


def can_delete(project, user):
    """A user can delete content in a project if the user is the project owner or
    if the user is in the collaborators group and the group has permission
    to delete content on the project

    :param project: project.models Project instance.
    :type project: models.Project.
    :param user: Django auth user instance.
    :type user: User.
    :returns:  bool -- returns if a user has permission \
            to delete something in a project
    """

    # With has_perm we can have different permissions for group
    return project.is_owner(user) or\
        (project.is_collaborator(user) and
            user.has_perm("project.can_delete"))


def can_change(project, user):
    """A user can change content in a project if the user is the project owner or
    if the user is in the collaborators group and the group has permission
    to change content in the project

    :param project: project.models Project instance.
    :type project: models.Project.
    :param user: Django auth user instance.
    :type user: User.
    :returns:  bool -- returns if a user has permission \
            to change something in a project"""

    return project.is_owner(user) or\
        (project.is_collaborator(user)
            and user.has_perm("project.can_change"))


def can_view(project, user):
    """Users can view content in a project if the project is public,
    or the user is the project owner, or the user is a project collaborator
    or the user is a project viewer

    :param project: project.models Project instance.
    :type project: models.Project
    :param user: Django auth user instance.
    :type user: User.
    :returns:  bool -- returns if a user has permission to view \
            something in a project"""

    return project.is_public\
        or project.is_owner(user)\
        or (project.is_collaborator(user) and user.has_perm("view"))\
        or (project.is_viewer(user) and user.has_perm("view"))


def get_nav_options(request):
    nav_options = []
    user = request.user

    if user.is_authenticated():
        nav_options.append({"url": "project:projects",
                            "name": "Projects"})

        if user.is_superuser:
            super_user_opts = [
                {"url": "account:users",
                 "name": "Users"},
                {"url": "admin:index",
                 "name": "Admin Pages"},
                {"url": "map:system-status",
                 "name": "System Status"}]

            for opt in super_user_opts:  # Add admin options
                nav_options.append(opt)

    nav_options.append({"url": "graph:graph_home", 
                         "name": "Graphs"}) 
    return nav_options
    
    
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


def render_project_form(
        request, project_id, post_form,
        get_form, template_path, success_url):
    """This is a main view called by other views that aim to render forms for
    Transmitters, Locations, Targets, and Deployments

    :param request: Django's http request object
    :type request: HttpRequest.
    :param project_id: Project's id to check user permissions
    :type project_id: str.
    :param post_form: form to render when receives a post request
    :type post_form: Projectform 
    :param get_form: form to render when receives a get request
    :type get_form: Projectform 
    :param template_path: The path of the template that will be rendered
    :type template_path: str.
    :param success_url: Url to redirect in case of success
    :type success_url: str.
    :returns:  HttpResponse -- Http response obj with a rendered page that \
            contains a form to add or edit Transmitters, \
            Locations, Targets, or Deployments
    """

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

def render_project_formset(
        request, project_id, post_formset,
        get_formset, template_path, success_url="", redirect_bool=True, extra_context=None):
    """This is a main view called by other views that aim to render forms for
    Transmitters, Locations, Targets, and Deployments

    :param request: Django's http request object
    :type request: HttpRequest.
    :param project_id: Project's id to check user permissions
    :type project_id: str.
    :param post_formset: Formset to render when receives a post request
    :type post_formset: ProjectFormSet from formset_factory(ProjectForm).
    :param get_formset: Formset to render when receives a get request
    :type get_formset: ProjectFormSet from formset_factory(ProjectForm).
    :param template_path: The path of the template that will be rendered
    :type template_path: str.
    :param success_url: Url to redirect in case of success
    :type success_url: str.
    :returns:  HttpResponse -- Http response obj with a rendered page that \
            contains a formset to add or edit Transmitters, \
            Locations, Targets, or Deployments
    """

    user = request.user
    project = get_project(project_id)
    nav_options = get_nav_options(request)
    thereis_newelement = None

    if can_change(project, user):
        if request.method == 'POST':
            formset = post_formset
            for form in formset:
                form.set_project(project)
            if formset.is_valid():
                formset.save()
                if redirect_bool:
                   return redirect(success_url)
                # For the bulk wizard page that after saving a formset, displays a new formset for new objects, instead of redirecting to another page
                # The request is returned, along with the formset in request.POST
                else:
                    return request

        elif request.method == 'GET':
            thereis_newelement = request.GET.get("new_element")
            formset = get_formset
            for form in formset:
                form.set_project(project)

        context = {"formset": formset,
                   "nav_options": nav_options,
                   "changed": thereis_newelement,
                   "project": project}

        if extra_context != None:
            if isinstance(extra_context, dict):
                context.update(extra_context)
            else:
                raise TypeError("Passed in non-dict for extra_context in render_project_formset")

        return render(request, template_path, context)
                      
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

def render_bulk_page(request, project, template_path, content):
    user = request.user
    nav_options = get_nav_options(request)

    if request.method == "GET":
        content["changed"] = request.GET.get("new_element")
        content["deleted"] = request.GET.get("deleted")

    if can_change(project, user):
        return render(
            request, template_path,
            content)

    else:
        return not_allowed_page(request)
