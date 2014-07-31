# File: qraat_ui/views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Q, Max, Min
import qraat, time, datetime, json, utm, math
from pytz import utc, timezone
from qraatview.models import Position, Track, Deployment, Site, Project
from qraat_ui.forms import Form
from decimal import Decimal

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
  if 'graph_dep' in request.GET and request.GET['graph_dep'] != "":
    graph_dep = int(request.GET['graph_dep'])
  else:
    graph_dep = None
  if 'display_type' in request.GET and request.GET['display_type'] != "":
    display_type = int(request.GET['display_type'])
  else:
    display_type = None
  
    
  if 'flot_index' in request.GET and request.GET['flot_index'] != "":
    flot_index = int(request.GET['flot_index'])
  else:
    flot_index = None
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
  #print 'deps', deps[0].ID
  #print 'req_deps', req_deps[0].ID
  print "req___deps", req_deps
  index_form = Form(deps=deps, req_deps=req_deps, data=request.GET or None)
  
  #Note: can change database by using "db_selected = Position"

  view_type = ""
  queried_data = []
  req_deps_int = []
  selected_data = []
  selected_message = "[ Nothing clicked, or no points detected nearby ]"
  selected_index = None
  selected_index_large = None
  
  
  #If only one dep is in the list of all deps, the view type is deployment.
  if len(deps) != 1:
    view_type = "public"
  else:
    view_type = "deployment"
  print "len deps", len(deps)
  print "len req_deps", len(req_deps)
 

  if len(req_deps) > 0:
    ''' Either a dep is passed by URL, or dep(s) selected in html form'''
    print "------- req deps exists"
   
    if (datetime_from == None) and (datetime_to == None) and (likelihood_low == None) and (likelihood_high == None) and (activity_low == None) and (activity_high == None): 
      req_deps_int.append(req_deps[0].ID)

      ''' /ui/project/1/deployment/63/
      When deployment page loads. No GET data from html form.
      Auto-filter by min/max range of likelihood & activity, for last 24 hrs
      of data in the db. Also set these filters as initial values of html 
      form. '''
      print "-------when deployment page first loads"

      dep_query = Position.objects.filter(deploymentID = req_deps[0].ID) 
      ''' Query db for min/max value for selected deployment.
        Used to automatically populate html form intial values. '''
      
      datetime_to_initial = float( dep_query.aggregate(Max('timestamp'))
                                    ['timestamp__max'] )
      datetime_to_str_initial = time.strftime('%Y-%m-%d %H:%M:%S',
                  time.localtime(float(datetime_to_initial-7*60*60)))
      datetime_from_initial = float(datetime_to_initial - 86400.00) #-24 hrs
      datetime_from_str_initial = time.strftime('%Y-%m-%d %H:%M:%S',
                  time.localtime(float(datetime_from_initial-7*60*60)))

      likelihood_low_initial = str ((dep_query.aggregate(Min('likelihood'))
                                    ['likelihood__min']) )
      likelihood_high_initial = str( (dep_query.aggregate(Max('likelihood'))
                                    ['likelihood__max']) )

      activity_low_initial = str( (dep_query.aggregate(Min('activity'))
                                    ['activity__min']) )
      activity_high_initial = str( (dep_query.aggregate(Max('activity'))
                                    ['activity__max']) )
  
      index_form.fields['datetime_from'].initial = datetime_from_str_initial
      index_form.fields['datetime_to'].initial = datetime_to_str_initial
      index_form.fields['likelihood_low'].initial = likelihood_low_initial
      index_form.fields['likelihood_high'].initial = likelihood_high_initial
      index_form.fields['activity_low'].initial = activity_low_initial
      index_form.fields['activity_high'].initial = activity_high_initial
 
      ''' FIXME: For blank form value(s), default them to min/max values of that dep. Notify the user that this happened. '''
      queried_data=[]
      queried_objects = Position.objects.filter(
                          deploymentID = req_deps[0].ID,
                          timestamp__gte = datetime_from_initial,
                          timestamp__lte = datetime_to_initial,
                          likelihood__gte = likelihood_low_initial,
                          likelihood__lte = likelihood_high_initial,
                          activity__gte = activity_low_initial,
                          activity__lte = activity_high_initial
                          ).order_by('deploymentID')


      for q in queried_objects:
        (lat, lon) = utm.to_latlon(float(q.easting), float(q.northing), 
          q.utm_zone_number, q.utm_zone_letter)
        date_string = time.strftime('%Y-%m-%d %H:%M:%S', 
          time.localtime(float(q.timestamp-7*60*60))) #FIXME

        queried_data.append((q.ID, q.deploymentID, float(q.timestamp), 
          float(q.easting), float(q.northing), q.utm_zone_number, 
          float(q.likelihood), float(q.activity), (lat, lon), 
          q.utm_zone_letter, date_string))

      queried_data_ids = [int(x[0]) for x in queried_data]
      selected_dep_start = queried_data_ids.index(64)
      print "dep starts", selected_dep_start

      # Note: To pass strings to js using json, use |safe in template.
    
    else: 
      ''' If any GET data from html form has been entered '''
      print "---------- public or deployment GET"

      req_deps_list = req_deps.values_list('ID', flat=True)    
      for dep in req_deps_list:
        req_deps_int.append(int(dep))
      print req_deps_int

      print datetime_from, datetime_to, likelihood_low, likelihood_high, activity_low, activity_high
      
      kwargs = {}
      #kwargs['deploymentID'] = '63'
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
    
      req_deps_IDs = req_deps.values_list('ID', flat=True)
      print "req_depsIDs", req_deps_IDs
      args_deps = []
      for dep in req_deps_IDs:
        args_deps.append(Q(deploymentID = str(dep)))
      args = Q()
      for each_args in args_deps:
        args = args | each_args
      #print "req_deps_IDs", req_deps_IDs
      print "args", args
   
      queried_objects = Position.objects.filter(*(args,), **kwargs).order_by('deploymentID')
      for row in queried_objects:
        (lat, lon) = utm.to_latlon(float(row.easting), 
            float(row.northing), row.utm_zone_number,
            row.utm_zone_letter)
        date_string = time.strftime('%Y-%m-%d %H:%M:%S', #FIXME
            time.localtime(float(row.timestamp-7*60*60)))

        queried_data.append((row.ID, row.deploymentID,
          float(row.timestamp), float(row.easting), 
          float(row.northing), row.utm_zone_number, 
          float(row.likelihood), float(row.activity), (lat, lon), 
          row.utm_zone_letter, date_string))
       
      
      queried_data_ids = [int(x[1]) for x in queried_data]
      
      if len(req_deps_int) > 0:
        selected_dep_start0 = queried_data_ids.index(req_deps_int[0])
        print "dep starts no GET", selected_dep_start0
      if len(req_deps_int) > 1:
        selected_dep_start1 = queried_data_ids.index(req_deps_int[1])
        print "dep starts no GET", selected_dep_start1 
      if len(req_deps_int) > 2:
        selected_dep_start2 = queried_data_ids.index(req_deps_int[2])
        print "dep starts no GET", selected_dep_start2 

     
      print "len queried", len(queried_data) 
      
      ''' For reference, the obsolete hardcoded query:
      pos_query = Position.objects.filter(
                          deploymentID = req_deps[0].ID,
                          timestamp__gte = datetime_start,
                          timestamp__lte = datetime_end,
                          likelihood__gte = likelihood_low,
                          likelihood__lte = likelihood_high,
                          activity__gte = activity_low,
                          activity__lte = activity_high) '''
  
#FIXME: Can remove this when nearest point on map is calculated in js.
  # Get clicked lat, lon from js event --> html form & convert to UTM
  if queried_data and lat_clicked and lng_clicked:    
    print "----------if anything is clicked"
    (easting_clicked, northing_clicked, utm_zone_number_clicked, utm_zone_letter_clicked) = utm.from_latlon(float(lat_clicked), float(lng_clicked))

  # Truncate northing and easting for the query
  # Divide by 10 (click needs to be closer) or 100 (less accurate) to increase the distance allowed between the clicked point and the actual point
    northing_clicked_trunc = (int(northing_clicked))/1000
    easting_clicked_trunc = (int(easting_clicked))/1000

  # Query the data that matches the northing and easting 
    filtered_list = queried_objects.filter(
      northing__startswith=northing_clicked_trunc, 
      easting__startswith=easting_clicked_trunc).order_by('-northing', '-easting')
    selected_list = []
    for f in filtered_list:
      selected_list.append(
        math.sqrt((northing_clicked - float(f.northing)) *
          (northing_clicked - float(f.northing))
        + (easting_clicked - float(f.easting)) * 
          (easting_clicked - float(f.easting))))
  
  # Get the index of the smallest distance
    if filtered_list:
      selected_message = ""
      selected_index = selected_list.index(min(selected_list))
  
  # Get the data corresponding to the selected index
      sel = filtered_list[selected_index]

      (lat_clicked_point, lng_clicked_point) = utm.to_latlon(
          float(sel.easting), float(sel.northing),
          sel.utm_zone_number, sel.utm_zone_letter)

      selected_data.append((
        float(lat_clicked),
        float(lng_clicked),
        sel.ID,                 # [2]: position ID
        sel.deploymentID,       # [3]: deploymentID
        float(sel.timestamp),   # [4]: timestamp UTC seconds
        float(sel.easting),     # [5]: easting
        float(sel.northing),    # [6]: northing
        sel.utm_zone_number,    # [7]: utm zone number
        float(sel.likelihood),  # [8]: likelihood
        float(sel.activity),    # [9]: activity
          (float(lat_clicked_point),    # [10][0]: db pt closest to click
          float(lng_clicked_point)),     # [10][1]: db pt closest to click
        time.strftime('%Y-%m-%d %H:%M:%S', # [11]: date string in Davis time
          time.localtime(float(sel.timestamp-7*60*60))),
        sel.utm_zone_letter     # utm zone letter
      ))

      #get index in the original filtered list, for the clicked point
      queried_data_IDs = [int(x[0]) for x in queried_data]
      selected_index_large = queried_data_IDs.index(
                                long(selected_data[0][2]))

                  # IF FLOT IS SELECTED:
          # Populate selected_data list with data based on index
          # FIXME could probably be changed to work the large list of data
  if flot_index:
    print "-------- if flot selected"
    print "flot index", flot_index
    if graph_dep == None:
      graph_dep = req_deps[0].ID

    #if transmitter is equal to req_deps[0].ID, do nothing
    #if transmitter is equal to req_deps[1].ID, add flot_index += selected_dep_start1
    #etc.

    queried_objects_dep = queried_objects.filter(
      deploymentID = str(graph_dep))
    queried_data_dep = []
    for i in queried_objects_dep:
      (lat, lon) = utm.to_latlon(float(i.easting), float(i.northing), 
          i.utm_zone_number, i.utm_zone_letter)
      date_string = time.strftime('%Y-%m-%d %H:%M:%S', 
          time.localtime(float(i.timestamp-7*60*60))) #FIXME
      queried_data_dep.append((i.ID, i.deploymentID, float(i.timestamp), 
          float(i.easting), float(i.northing), i.utm_zone_number, 
          float(i.likelihood), float(i.activity), (lat, lon), 
          i.utm_zone_letter, date_string))
    
    print "graph_dep", graph_dep
    print "len data dep", len(queried_data_dep)
    selected_data.append((
        None,   # [0]: nothing clicked
        None,   # [1]: nothing clicked
        queried_data_dep[flot_index][0],   # [2]: ID
        queried_data_dep[flot_index][1],   # [3]: deploymentID
        float(queried_data_dep[flot_index][2]), # [4]: timestamp
        float(queried_data_dep[flot_index][3]), # [5]: easting
        float(queried_data_dep[flot_index][4]), # [6]: northing
        queried_data[flot_index][5], # [7]: utm zone number
        float(queried_data_dep[flot_index][6]), # [8]: likelihood
        float(queried_data_dep[flot_index][7]), # [9]: activity
        # [10]: tuple: [10][0]: lat, [10][1]: lon
        (float(queried_data_dep[flot_index][8][0]),
        float(queried_data_dep[flot_index][8][1])),
        # [11] Davis time string converted from timestamp UTC seconds
        time.strftime('%Y-%m-%d %H:%M:%S', 
          time.localtime(float(queried_data_dep[flot_index][2]-7*60*60))),
        # [12] utm zone letter
        queried_data_dep[flot_index][9]
      ))
  
  print "large", selected_index_large
  print "small", selected_index
  
  context = {
            #public, deployment, project, etc.
            'view_type': json.dumps(view_type),
            'deps_list': json.dumps(req_deps_int),
            'deps': req_deps_int,
            #plot & related data
            'pos_data': json.dumps(queried_data),
            #for getting the no. of positions
            'positions': queried_data,
            #for plotting the site markers
            'siteslist': json.dumps(sites), 
            #for displaying html form
            #'form': Form(deps=deps, data=request.GET or None), 
            'form': index_form,
            'form_list': list(index_form),
            #if sites should be shown
            'site_checked': json.dumps(site_checked), 
            #clicked point's data, note: string
            'selected_data': json.dumps(selected_data), 
            #actvty vs lklhood graphed
            'graph_data': json.dumps(graph_data),
            'graph_dep': json.dumps(graph_dep),
            'graph_dep_django': graph_dep,
            #if pos successfully clicked
            'selected_message': selected_message, 
            #map-clicked i in filtered pos_data
            'selected_index': selected_index, 
            #clicked i in pos_data
            'selected_index_large': selected_index_large, 
            #flot selected i in pos_data
            'flot_index': json.dumps(flot_index), 
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
  # TODO filter deps by form data. 
  if request.GET.getlist('deployment') != None:
    req_deps = Deployment.objects.filter(ID__in=request.GET.getlist('deployment'))
  else: 
    req_deps = []

  deps = Deployment.objects.filter(is_active=True,
          projectID__in=Project.objects.filter(
            is_public=True).values('ID'))

  context = get_context(request, deps, req_deps)
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
    
  positions = Position.objects.filter(deploymentID__in=deps.values("ID") )
  if len(positions) >0:
    context = get_context(request, deps, deps)
  else:
    context = {}

  return render(request, 'qraat_ui/index.html', context)

def view_by_target(request, target_id): 
  ''' Compile a list of deployments associated with `target_id`. ''' 
  return HttpResponse('Not implemneted yet. (targetID=%s)' % target_id)

def view_by_tx(request, tx_id): 
  ''' Compile a list of deployments associated with `tx_id`. ''' 
  return HttpResponse('Not implemneted yet. (txID=%s)' % tx_id)
