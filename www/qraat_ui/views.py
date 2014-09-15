# File: qraat_ui/views.py
#
# TODO Clean up get_context(). The way it's written necessitates a redundant 
#      query in the calling functions, e.g. get_by_dep() and download_by_dep(). 
# 
# TODO Cache last query (result of get_context()) for download.  
#
# TODO Post handler for "Submit Form"? 

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Q, Max, Min
from django.contrib.auth.decorators import login_required
from qraatview.views import get_nav_options, not_allowed_page, can_view
from qraatview.utils import DateTimeEncoder
import qraatview.rest_api as rest_api
import qraat, time, datetime, json, utm, math, copy
from pytz import utc, timezone
from qraatview.models import Position, Deployment, Site, Project
from qraat_ui.forms import Form
from decimal import Decimal

import csv
import qraat



def get_context(request, deps=[], req_deps=[]):
  
  if 'sites' in request.GET:
    site_checked = 1
  else:
    site_checked = None
  if 'data_type' in request.GET:
    data_type = request.GET['data_type']
  else:
    data_type = None
  if 'datetime_from' in request.GET:
    datetime_from = request.GET['datetime_from']
  else:
    datetime_from = None
    datetime_from_sec = None
  if 'datetime_to' in request.GET:
    datetime_to = request.GET['datetime_to']
  else: 
    datetime_to = None
    datetime_to_sec = None
  if 'likelihood_low' in request.GET:
    likelihood_low = request.GET['likelihood_low']
  else:
    likelihood_low = None
  if 'likelihood_high' in request.GET:
    likelihood_high = request.GET['likelihood_high']
  else:
    likelihood_high = None
  if 'activity_low' in request.GET:
    activity_low = request.GET['activity_low']
  else:
    activity_low = None
  if 'activity_high' in request.GET:
    activity_high = request.GET['activity_high']
  else:
    activity_high = None
  if 'graph_data' in request.GET and request.GET['graph_data'] != "":
    graph_data = int(request.GET['graph_data'])
  else:
    graph_data = None
  #if 'graph_dep' in request.GET and request.GET['graph_dep'] != "":
  #  graph_dep = int(request.GET['graph_dep'])
  #elif len(deps) > 0: 
  #  graph_dep = deps[0].ID
  if 'display_type' in request.GET and request.GET['display_type'] != "":
    display_type = int(request.GET['display_type'])
  else:
    display_type = None
  
    
  if 'flot_index' in request.GET and request.GET['flot_index'] != "":
    flot_index = int(request.GET['flot_index'])
  else:
    flot_index = None
  if 'flot_dep' in request.GET and request.GET['flot_dep'] !="":
    flot_dep = int(request.GET['flot_dep'])
  else:
    flot_dep = None
  if ('lat_clicked' in request.GET) and (request.GET['lat_clicked'] != ""):
    lat_clicked = request.GET['lat_clicked']
  else:
    lat_clicked = None
  if ('lng_clicked' in request.GET) and (request.GET['lng_clicked'] != ""):
    lng_clicked = request.GET['lng_clicked']
  else:
    lng_clicked = None


  #Site locations
  sites = []
  for s in Site.objects.all():
    sites.append((
      s.ID, s.name, s.location, float(s.latitude), float(s.longitude), 
      float(s.easting), float(s.northing), s.utm_zone_number, 
      s.utm_zone_letter, float(s.elevation)))
  index_form = Form(deps=deps, req_deps=req_deps, data=request.GET or None)
  
  view_type = ""
  queried_data = []
  req_deps_int = [] # dep_id's
  req_deps_IDs = []
  #selected_data = []
  selected_message = "[ Nothing clicked, or no points detected nearby ]"
  selected_index = None
  selected_index_large = None
  map_dep_index = None
  map_pos_index = None 
  # If only one dep is in the list of all deps, the view type is deployment.
  # FIXME arbitrary sets of deployments, not dependent on public or private. 
  if len(deps) != 1:
    view_type = "public"
  else:
    view_type = "deployment"
  print "len deps", len(deps)
  print "len req_deps", len(req_deps)
 

  if flot_index == None and lat_clicked==None and lng_clicked==None:
    if len(req_deps) > 0:
      graph_dep = req_deps[0].ID
    else:
      graph_dep = deps[0].ID


  if len(req_deps) > 0:
    ''' Either a dep is passed by URL, or dep(s) selected in html form'''
    print "------- req deps exists"
   
    if (datetime_from == None) and (datetime_to == None) and (likelihood_low == None) and (likelihood_high == None) and (activity_low == None) and (activity_high == None): 
      req_deps_int.append(req_deps[0].ID) # /ui/project/X/deployment/Y

      ''' /ui/project/1/deployment/63/
      When deployment page loads. No GET data from html form.
      Auto-filter by min/max range of likelihood & activity, for last 24 hrs
      of data in the db. Also set these filters as initial values of html 
      form. '''
      print "-------when deployment page first loads"

      #dep_query = Position.objects.filter(deploymentID__in = map(lambda(row) : row.ID, req_deps)) 
      dep_query = Position.objects.filter(deploymentID = req_deps[0].ID)
      ''' Query db for min/max value for selected deployment.
        Used to automatically populate html form intial values. '''
      
      queried_data=[]
      
      if len(dep_query) == 0: 
        print "No positions, returning empty context."
      
      else: # Set default form vlaues, populate queried_data. 
        # Select the last day of data for deployment. 
        datetime_to_initial = float( dep_query.aggregate(Max('timestamp'))
                                      ['timestamp__max'] )
        datetime_to_str_initial = time.strftime('%Y-%m-%d %H:%M:%S',
                    time.localtime(float(datetime_to_initial-7*60*60)))
      
        datetime_from_min_initial = float( dep_query.aggregate(
                                Min('timestamp'))['timestamp__min'] )
        datetime_from_day_initial = float(datetime_to_initial - 86400.00) 
          # minus 24 hrs
        if datetime_from_day_initial < datetime_from_min_initial:
          datetime_from_initial = datetime_from_min_initial
        else:
          datetime_from_initial = datetime_from_day_initial
        datetime_from_str_initial = time.strftime('%Y-%m-%d %H:%M:%S',
                    time.localtime(float(datetime_from_initial-7*60*60)))

        likelihood_low_initial = dep_query.aggregate(Min('likelihood'))['likelihood__min']
        likelihood_high_initial = dep_query.aggregate(Max('likelihood'))['likelihood__max']

        activity_low_initial = dep_query.aggregate(Min('activity'))['activity__min']
        activity_high_initial = dep_query.aggregate(Max('activity'))['activity__max']
    
        index_form.fields['datetime_from'].initial = datetime_from_str_initial
        index_form.fields['datetime_to'].initial = datetime_to_str_initial
        index_form.fields['likelihood_low'].initial = likelihood_low_initial
        index_form.fields['likelihood_high'].initial = likelihood_high_initial
        index_form.fields['activity_low'].initial = activity_low_initial
        index_form.fields['activity_high'].initial = activity_high_initial
   
        ''' FIXME: For blank form value(s), default them to min/max values of that dep. Notify the user that this happened. '''
        
        # Query data. 
        queried_objects = Position.objects.filter(
                            deploymentID = req_deps[0].ID,
                            timestamp__gte = datetime_from_initial,
                            timestamp__lte = datetime_to_initial,
                            likelihood__gte = likelihood_low_initial,
                            likelihood__lte = likelihood_high_initial,
                            activity__gte = activity_low_initial,
                            activity__lte = activity_high_initial
                            )

        for q in queried_objects:
          #(lat, lon) = utm.to_latlon(float(q.easting), float(q.northing), 
          #  q.utm_zone_number, q.utm_zone_letter)
          date_string = time.strftime('%Y-%m-%d %H:%M:%S', 
                  time.localtime(float(q.timestamp-7*60*60))) #FIXME: Hardcode timestamp conversion 

          queried_data.append((q.ID, q.deploymentID, float(q.timestamp), 
            float(q.easting), float(q.northing), q.utm_zone_number, 
            float(q.likelihood), float(q.activity), 
            (float(q.latitude), float(q.longitude)), 
            q.utm_zone_letter, date_string))

        # Note: To pass strings to js using json, use |safe in template.
    
    else: 
      ''' If any GET data from html form has been entered '''
      print "---------- public or deployment GET"

      req_deps_list = req_deps.values_list('ID', flat=True)    
      for dep in req_deps_list:
        req_deps_int.append(int(dep))
      
      kwargs = {}
      if datetime_from:
        kwargs['timestamp__gte'] =  float( time.mktime (datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple()) ) + 7*60*60
      if datetime_to:
        kwargs['timestamp__lte'] = float( time.mktime (datetime.datetime.strptime(datetime_to, '%Y-%m-%d %H:%M:%S').timetuple()) ) + 7*60*60
      if likelihood_low:
        kwargs['likelihood__gte'] = likelihood_low
      if likelihood_high:
        kwargs['likelihood__lte'] = likelihood_high
      if activity_low:
        kwargs['activity__gte'] = activity_low
      if activity_high:
        kwargs['activity__lte'] = activity_high
    
      ''' FIXME. This limits the list of req_deps to 4, otherwise the points
      will display as the large default google maps markers.'''
      req_deps_ID = req_deps.values_list('ID', flat=True)
      #uncomment to stop limiting list to 4
      #req_deps_IDs = req_deps.values_list('ID', flat=True)
      #Delete the following 4 lines to stop limiting the list 
      req_deps_IDs = []    
      for dep in req_deps_ID:
        if len(req_deps_IDs) < 4:
          req_deps_IDs.append(int(dep))
        
      print "req_depsIDs", req_deps_IDs
      args_deps = []
      for dep in req_deps_IDs:
        args_deps.append(Q(deploymentID = str(dep)))
      args = Q()
      for each_args in args_deps:
        args = args | each_args
  
      # Query data. 
      if int(data_type) == 1: 
        queried_objects = Position.objects.filter(*(args,), **kwargs)
      elif int(data_type) == 2: 
        queried_objects = Position.objects.raw(
           '''SELECT * FROM position
                JOIN track_pos ON track_pos.positionID = position.ID
               WHERE position.deploymentID = %s
                 AND position.timestamp >= %s AND position.timestamp <= %s
                 AND likelihood >= %s AND likelihood <= %s
                 AND activity >= %s AND activity <= %s
               ORDER BY position.timestamp''', (req_deps[0].ID, 
            qraat.util.datetime_to_timestamp(datetime_from),
            qraat.util.datetime_to_timestamp(datetime_to),
            likelihood_low, likelihood_high, 
            activity_low, activity_high, ))

      else: 
        raise Exception("Somethign is wrong.")
     
      for row in queried_objects:
        #(lat, lon) = utm.to_latlon(float(row.easting), 
        #    float(row.northing), row.utm_zone_number,
        #    row.utm_zone_letter)
        date_string = time.strftime('%Y-%m-%d %H:%M:%S', #FIXME
            time.localtime(float(row.timestamp-7*60*60)))

        queried_data.append((row.ID, row.deploymentID,
          float(row.timestamp), float(row.easting), 
          float(row.northing), row.utm_zone_number, 
          float(row.likelihood), float(row.activity), 
          (float(row.latitude), float(row.longitude)), 
          row.utm_zone_letter, date_string))
       
     
      ''' For reference, the obsolete hardcoded query:
      pos_query = Position.objects.filter(
                          deploymentID = req_deps[0].ID,
                          timestamp__gte = datetime_start,
                          timestamp__lte = datetime_end,
                          likelihood__gte = likelihood_low,
                          likelihood__lte = likelihood_high,
                          activity__gte = activity_low,
                          activity__lte = activity_high) '''
  
  context = {
            #public, deployment, project, etc.
            'view_type': json.dumps(view_type),
            
            'deps_list': json.dumps(req_deps_int),
            
            'deps': req_deps_int,

            'deps_limit4': req_deps_IDs,
            
            #plot & related data
            'pos_data': json.dumps(queried_data),
            
            #for getting the no. of positions
            'positions': queried_data,
            
            #for plotting the site markers
            'siteslist': json.dumps(sites), 
            
            #for displaying html form
            #'form': Form(deps=deps, data=request.GET or None), 
            'form': index_form,
            
            #if sites should be shown
            'site_checked': json.dumps(site_checked), 
            
            #clicked point's data, note: string
            #'selected_data': json.dumps(selected_data), 

            # Flag, either likelihood (1, default) or activity data (2) 
            'graph_data': json.dumps(graph_data),

            # Deployment selected for graph
            'graph_dep': json.dumps(graph_dep),
            'graph_dep_django': graph_dep,
            
            #graph queried data as lines or points on map
            'display_type': json.dumps(display_type),
            'data_type': json.dumps(data_type), #position vs. track 
            }
  
  return context

def index(request):
  ''' Compile a list of public deployments, make this available. 
      Don't initially display anything. ''' 

  #''' SELECT * FROM deployment JOIN project 
  #      ON deployment.projectID = project.ID 
  #   WHERE project.is_public = True ''' 
  
  nav_options = get_nav_options(request)

  if request.GET.getlist('deployment') != None:
    req_deps = Deployment.objects.filter(ID__in=request.GET.getlist('deployment'))
  else: 
    req_deps = []

  deps = Deployment.objects.filter(is_active=True,
          projectID__in=Project.objects.filter(
            is_public=True).values('ID'))

  context = get_context(request, deps, req_deps)
  context["nav_options"] = nav_options
  return render(request, 'qraat_ui/index.html', context)

def view_by_dep(request, project_id, dep_id):
  ''' Compile a list of deployments associated with `dep_id`. ''' 
  try:
    project = Project.objects.get(ID=project_id)
  except ObjectDoesNotExist:
    return HttpResponse("We didn't find this project") 
  
  if not project.is_public:
    if request.user.is_authenticated():
      user = request.user
      if project.is_owner(user)\
           or (user.has_perm("can_view")
               and (project.is_collaborator(user)
                    or project.is_viewer(user))):

        deps = project.get_deployments().filter(ID=dep_id)
      else:
        return HttpResponse("You're not allowed to view this.")
    
    else:
      return HttpResponse("You're not allowed to visualize this")

  else:
    deps = project.get_deployments().filter(ID=dep_id)
   
  context = get_context(request, deps, deps)

  nav_options = get_nav_options(request)
  context["nav_options"] = nav_options
  context["project"] = project

  return render(request, 'qraat_ui/index.html', context)


def download_by_dep(request, project_id, dep_id): 
  print request
  
  try:
    project = Project.objects.get(ID=project_id)
  except ObjectDoesNotExist:
    return HttpResponse("We didn't find this project") 
  
  if not project.is_public:
    if request.user.is_authenticated():
      user = request.user
      if project.is_owner(user)\
           or (user.has_perm("can_view")
               and (project.is_collaborator(user)
                    or project.is_viewer(user))):

        deps = project.get_deployments().filter(ID=dep_id)
      else:
        return HttpResponse("You're not allowed to view this.")
    
    else:
      return HttpResponse("You're not allowed to visualize this")

  else:
    deps = project.get_deployments().filter(ID=dep_id)
  
  context = get_context(request, deps, deps)

  response = HttpResponse(content_type='text/csv')
  response['Content-Disposition'] = 'attachement; filename="position_dep%s.csv"' % dep_id

  writer = csv.writer(response)
  writer.writerow(['ID', 'deploymentID', 'timestamp', 'easting', 'northing', 'zone', 
                   'datetime', 'latitude', 'longitude', 'likelihood', 'activity'])
  for row in json.loads(context['pos_data']):
    writer.writerow([ row[0], row[1], row[2], row[3], row[4], str(row[5]) + row[9], 
                      row[10], row[8][0], row[8][1], row[6], row[7] ])
  return response
  

def view_by_target(request, target_id): 
  ''' Compile a list of deployments associated with `target_id`. ''' 
  return HttpResponse('Not implemneted yet. (targetID=%s)' % target_id)


def view_by_tx(request, tx_id): 
  ''' Compile a list of deployments associated with `tx_id`. ''' 
  return HttpResponse('Not implemneted yet. (txID=%s)' % tx_id)


@login_required(login_url="auth/login")
def system_status(
            request,
            static_field="siteID",
            obj="telemetry",
            excluded_fields=["ID", "siteID", "timestamp",
                "datetime", "timezone"]):

    if request.GET.get("start_date"):
        start_date = request.GET.get("start_date")
    else:
        start_date = (datetime.datetime.now() -
                datetime.timedelta(1)).strftime("%m/%d/%Y %H:%M:%S")

    model_obj = rest_api.get_model_type(obj)
    obj_fields_keys = [field.name for field in model_obj._meta.fields
        if field.name not in excluded_fields]
    static_field_values = model_obj.objects.values_list(static_field, flat=True).distinct()
    fields = copy.copy(request.GET.getlist("field"))
    
    # Replaces field's name for selected field's value
    sel_static_values = request.GET.getlist("filter_field")
    for sel_values in sel_static_values:
        key, value = sel_values.split(",")
        fields[fields.index(key)] = sel_values 

    content = {}
    content = dict(
                nav_options=get_nav_options(request),
                fields=json.dumps(fields),
                static_field_values=static_field_values,
                obj_fields_keys=obj_fields_keys,
                start_date= start_date,
                static_field=json.dumps(static_field))

    try:
        data = rest_api.get_model_data(request)
    except Exception, e:
        print e
        content["data"] = json.dumps(None)
    else:
        content["data"] = json.dumps(rest_api.json_parse(data), cls=DateTimeEncoder)

    return render(request, "qraat_ui/system_status.html", content)


@login_required(login_url="auth/login")
def est_status(
            request,
            static_field="deploymentID",
            obj="est",
            excluded_fields=["ID", "deploymentID", "siteID",
                "timestamp"]):

    if request.GET.get("start_date"):
        start_date = request.GET.get("start_date")
    else:
        start_date = (datetime.datetime.now() -
                datetime.timedelta(1)).strftime("%m/%d/%Y %H:%M:%S")

    model_obj = rest_api.get_model_type(obj)
    obj_fields_keys = [field.name for field in model_obj._meta.fields
        if field.name not in excluded_fields]
    static_field_values = model_obj.objects.values_list(static_field, flat=True).distinct()
    fields = copy.copy(request.GET.getlist("field"))
    
    # Replaces field's name for selected field's value
    sel_static_values = request.GET.getlist("filter_field")
    for sel_values in sel_static_values:
        key, value = sel_values.split(",")
        fields[fields.index(key)] = sel_values 

    content = {}
    content = dict(
                nav_options=get_nav_options(request),
                fields=json.dumps(fields),
                static_field_values=static_field_values,
                obj_fields_keys=obj_fields_keys,
                start_date= start_date,
                static_field=json.dumps(static_field))

    try:
        data = rest_api.get_model_data(request)
    except Exception, e:
        print e
        content["data"] = json.dumps(None)
    else:
        content["data"] = json.dumps(rest_api.json_parse(data), cls=DateTimeEncoder)

    return render(request, "qraat_ui/est_status.html", content)


@login_required(login_url="/auth/login")
def generic_graph(
                request,
                objs=["telemetry", "position", "deployment", "est"],
                excluded_fields=[
                    "siteID", "datetime", "timezone",
                    "utm_zone_number", "utm_zone_letter"],
                template="qraat_ui/generic_graph.html"):

    nav_options = get_nav_options(request)
    content = {}
    content = dict(
            objs=objs,
            nav_options=nav_options,
            excluded_fields=json.dumps(excluded_fields),
            selected_obj=json.dumps(request.GET.get("obj")),
            offset=request.GET.get("offset"),
            n_items=request.GET.get("n_items")
            )
    
    fields = request.GET.getlist("field")
    content["fields"] = json.dumps(fields)

    try:
        data = rest_api.get_model_data(request) 
    except Exception, e:
        print e
        content["data"] = json.dumps(None)
    else:
        content["data"] = json.dumps(rest_api.json_parse(data), cls=DateTimeEncoder)

    return render(
        request, template, content)
