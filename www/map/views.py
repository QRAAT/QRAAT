#!/usr/bin/python
# -*- coding: utf-8 -*-
# File: map/views.py
#
# TODO Cache last query (result of get_context()) for download.
#
# TODO Post handler for "Submit Form"?

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.shortcuts import render, render_to_response, \
    get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.db.models import Q, Max, Min
from django.contrib.auth.decorators import login_required
from viewsutils import get_nav_options, not_allowed_page, can_view
import rest_api as rest_api
import utils
import qraat
import time
import datetime
import json
import utm
import math
import copy
from pytz import utc, timezone
from project.models import Position, Deployment, Site, Project, Tx
from map.forms import Form
from decimal import Decimal

import csv
import qraat
import kmlGeneratorModule

# For view /ui/project/X/deployment/Y, initial time range for data to display.

INITIAL_DATA_WINDOW = 60 * 60 * 4


def get_context(request, deps=[], req_deps=[]):
    print "in get_context"
    req_deps_list = req_deps.values_list('ID', flat=True)
    req_deps_IDs = []
    for dep in req_deps_list:
        req_deps_IDs.append(int(dep))

    if 'sites' in request.GET:
        if request.GET['sites'] == 'off':
            sites_checked = 0
        else:
            sites_checked = 1
        sites_checked = 1
    else:
        sites_checked = 1
    if 'points' in request.GET:
        points_checked = 1
    else:
        points_checked = None
    if 'colorpoints' in request.GET:
        colorpoints_checked = 1
    else:
        colorpoints_checked = None
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = int(request.GET['data_type'])
    else:
        data_type = 1
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
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None
    #dictionary.get(key, default=None), returns None if the key isn't
    #in the dictionary instead of throwing an exception
    # TODO: Change above
    covariance_low = request.GET.get('covariance_low')
    covariance_high = request.GET.get('covariance_high')

    if 'graph_data' in request.GET and request.GET['graph_data'] != '':
        graph_data = int(request.GET['graph_data'])
    else:
        graph_data = None

    if 'display_type' in request.GET and request.GET['display_type'] \
        != '':
        display_type = int(request.GET['display_type'])
    else:
        display_type = None
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None

    if 'flot_dep' in request.GET and request.GET['flot_dep'] != '':
        flot_dep = int(request.GET['flot_dep'])
    else:
        flot_dep = None
    if 'lat_clicked' in request.GET and request.GET['lat_clicked'] \
        != '':
        lat_clicked = request.GET['lat_clicked']
    else:
        lat_clicked = None
    if 'lng_clicked' in request.GET and request.GET['lng_clicked'] \
        != '':
        lng_clicked = request.GET['lng_clicked']
    else:
        lng_clicked = None
    # If datetime_to doesn't exist, try to get the latest time from all deployments. Set it to 0 otherwise.
    # If there's no datetime_from, set it some interval before datetime_to
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None
    if 'datetime_to' in request.GET:
        datetime_to = request.GET['datetime_to']
    else:
        args = Q()
        for dep in req_deps_IDs:
            args = args | Q(deploymentID=str(dep))
        datetime_to = Position.objects.filter(args).aggregate(Max('timestamp'))['timestamp__max']
        if datetime_to != None:
            datetime_to = utils.strftime(utils.timestamp_todate(datetime_to))
    if 'lines' in request.GET:
        lines_checked = 0 # Not on by default TODO: currently does nothing?
    else:
        lines_checked = None
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    else:
        data_type = 1
    if 'likelihood_low' in request.GET:
        likelihood_low = request.GET['likelihood_low']
    else:
        likelihood_low = None
    if 'datetime_from' in request.GET:
        datetime_from = request.GET['datetime_from']
    else:
        if datetime_to != None:
            datetime_from = utils.strftime(utils.timestamp_todate(utils.datelocal_totimestamp(utils.strptime(datetime_to)) - INITIAL_DATA_WINDOW))
        else:
            datetime_from = None 

    print 'in get_context datetimefrom and to', datetime_from, datetime_to
  # Site locations

    sites = []
    for s in Site.objects.all():
        sites.append((
            s.ID,
            s.name,
            s.location,
            float(s.latitude),
            float(s.longitude),
            float(s.easting),
            float(s.northing),
            s.utm_zone_number,
            s.utm_zone_letter,
            float(s.elevation),
            ))
    index_form = Form(deps=deps, req_deps=req_deps, data=request.GET
                      or None)

    view_type = ''
    queried_data = []

  # selected_data = []

    selected_message = \
        '[ Nothing clicked, or no points detected nearby ]'
    selected_index = None
    selected_index_large = None
    map_dep_index = None
    map_pos_index = None

  # If only one dep is in the list of all deps, the view type is deployment.
  # FIXME arbitrary sets of deployments, not dependent on public or private.

    if len(deps) != 1:
        view_type = 'public'
    else:
        view_type = 'deployment'
    print 'len deps', len(deps)
    print 'len req_deps', len(req_deps)

    print '------- req deps exists'

    queried_objects = []
    kwargs = {}
    if datetime_to != None: # There is at least one datapoint
        kwargs['timestamp__gte'] = utils.datelocal_totimestamp(utils.strptime(datetime_from))
        kwargs['timestamp__lte'] = utils.datelocal_totimestamp(utils.strptime(datetime_to))
        if int(data_type) == 1: # Raw positions
            for i in range(len(req_deps)):
                queried_objects.append([])
                print '----~~~~~ here, kwargs and ID', kwargs, req_deps[i].ID
                queried_objects[i] = \
                    Position.objects.filter(deploymentID=req_deps[i].ID,
                        **kwargs)
        elif int(data_type) == 2: # Tracks
            print '~~~~....... here, tracks'
            for i in range(len(req_deps)):
                print '~~~....~~' ,req_deps[i].ID, kwargs['timestamp__gte'], kwargs['timestamp__lte']
                queried_objects.append([])
                queried_objects[i] = \
                    Position.objects.raw('''SELECT * FROM position
                JOIN track_pos ON track_pos.positionID = position.ID
               WHERE position.deploymentID = %s
                 AND position.timestamp >= %s AND position.timestamp <= %s''',
                    ( 
                    req_deps[i].ID,
                    kwargs['timestamp__gte'],
                    kwargs['timestamp__lte'],
                    ))
            print 'here.....~~~~'
        else:
            raise Exception("data_type isn't 1 or 2")

        filter_values = [[],[],[],[]] # Having inner arrays instead of just a min/max value is a remnant  of wanting to know the min/max for each deployment
        for i in range(len(req_deps)):
            # Get the max/min filter values of each deployment
            if likelihood_low == None:
                temp = queried_objects[i].aggregate(Min('likelihood'))['likelihood__min']
                if temp != None:
                    filter_values[0].append(temp)
            if likelihood_high == None:
                temp = queried_objects[i].aggregate(Max('likelihood'))['likelihood__max']
                if temp != None:
                    filter_values[1].append(temp)
            if activity_low == None:
                temp = queried_objects[i].aggregate(Min('activity'))['activity__min']
                if temp != None:
                    filter_values[2].append(temp)
            if activity_high == None:
                temp = queried_objects[i].aggregate(Max('activity'))['activity__max']
                if temp != None:
                    filter_values[3].append(temp)

        index_form.fields['datetime_from'].initial = datetime_from
        index_form.fields['datetime_to'].initial = datetime_to

        # Get the ceiling/floor to 2 decimal places. 
        if likelihood_low != None:
            index_form.fields['likelihood_low'].initial = likelihood_low
        else:
            if len(filter_values[0]) != 0:
                index_form.fields['likelihood_low'].initial = round(math.floor(min(filter_values[0])*100),2)/100
            else:
                index_form.fields['likelihood_low'].initial = 0
        if likelihood_low != None:
            index_form.fields['likelihood_high'].initial = likelihood_high
        else:
            if len(filter_values[1]) != 0:
                index_form.fields['likelihood_high'].initial = round(math.ceil(min(filter_values[1])*100),2)/100
            else:
                index_form.fields['likelihood_high'].initial = 1
        if activity_low != None:
            index_form.fields['activity_low'].initial = activity_low
        else:
            if len(filter_values[2]) != 0:
                index_form.fields['activity_low'].initial = round(math.floor(min(filter_values[2])*100),2)/100
            else:
                index_form.fields['activity_low'].initial = 0
        if activity_low != None:
            index_form.fields['activity_high'].initial = activity_high
        else:
            if len(filter_values[3]) != 0:
                index_form.fields['activity_high'].initial = round(math.ceil(min(filter_values[3])*100),2)/100
            else:
                index_form.fields['activity_high'].initial = 1
    else: # No data at all
        kwargs['timestamp__gte'] = None
        kwargs['timestamp__lte'] = None

    queried_data = sort_query_results(queried_objects)

    context = {  # public, deployment, project, etc.
                 # plot & related data
                 # for getting the no. of positions
                 # for plotting the site markers
                 # for displaying html form
                 # 'form': Form(deps=deps, data=request.GET or None),
                 # if sites should be shown
                 # points
                 # lines
                 # clicked point's data, note: string
                 # 'selected_data': json.dumps(selected_data),
                 # Flag, either likelihood (1, default) or activity data (2)
                 # Deployment selected for graph
                 # graph queried data as lines or points on map
                 # position vs. track
                 # datetime_from
                 # datetime_to
        'view_type': json.dumps(view_type),
        'deps_list': json.dumps(req_deps_IDs),
        'deps': req_deps_IDs,
        'deps_limit4': req_deps_IDs,
        'pos_data': json.dumps(queried_data),
        'positions': queried_data,
        'siteslist': json.dumps(sites),
        'form': index_form,
        'sites_checked': json.dumps(sites_checked),
        'points_checked': json.dumps(points_checked),
        'colorpoints_checked': json.dumps(colorpoints_checked),
        'lines_checked': json.dumps(lines_checked),
        'graph_data': json.dumps(graph_data),
        'display_type': json.dumps(display_type),
        'data_type': json.dumps(data_type),
        'datetime_from': kwargs['timestamp__gte'],
        'datetime_to': kwargs['timestamp__lte']
        }

    return context


def sort_query_results(queried_objects):
    ''' Choose highest likelihood position for each timestamp 
      and sort query data by timestamp. '''
    print "in sort_query_results"

  # use dictionary to remove duplicates (positions with same timestamp)
    queried_data = []  # data ordered by timestamp
    for i in range(0,len(queried_objects)):
        query_dictionary = {}  # key=timestamp, value=query_row
        for row in queried_objects[i]:
            if row.timestamp not in query_dictionary:
                query_dictionary[row.timestamp] = row
            elif row.likelihood \
                > query_dictionary[row.timestamp].likelihood:
                query_dictionary[row.timestamp] = row  # replaces existing value if new likelihood is greater
            else:
                pass  # existing likelihood is greater

        timestamps = sorted(query_dictionary.keys())

        queried_data.append([]);
        for timestamp in timestamps:
            row = query_dictionary[timestamp]
            date_string = utils.strftime(utils.timestamp_todate(row.timestamp))

            queried_data[i].append((
                row.ID,
                row.deploymentID,
                float(row.timestamp),
                float(row.easting),
                float(row.northing),
                row.utm_zone_number,
                float(row.likelihood),
                float(row.activity),
                (float(row.latitude), float(row.longitude)),
                row.utm_zone_letter,
                date_string,
                ))

    return queried_data


def index(request):
    ''' Compile a list of public deployments, make this available. 
      Don't initially display anything. '''

  # ''' SELECT * FROM deployment JOIN project
  #      ON deployment.projectID = project.ID
  #   WHERE project.is_public = True '''

    nav_options = get_nav_options(request)

    if request.GET.getlist('deployment') != None:
        req_deps = \
            Deployment.objects.filter(ID__in=request.GET.getlist('deployment'
                ))
    else:
        req_deps = []

    deps = Deployment.objects.filter(is_active=True,
            projectID__in=Project.objects.filter(is_public=True).values('ID'
            ))

    context = get_context(request, deps, req_deps)
    context['nav_options'] = nav_options
    return render(request, 'map/index.html', context)


def view_all_dep(request, project_id):
    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
        raise Http404
    deployments = project.get_deployments()
    dep_ids = []
    for dep in deployments:
        dep_ids.append(dep.ID)
    return view_by_dep(request, project_id, '+'.join(map(str, dep_ids)))

def view_by_dep(request, project_id, dep_id):
    ''' Compile a list of deployments associated with `dep_id`. '''

    dep_id = dep_id.split("+")
    dep_id = [int(i) for i in dep_id]

    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
        raise Http404

    if not project.is_public:
        if request.user.is_authenticated():
            user = request.user
            if project.is_owner(user) \
                or user.has_perm('project.can_view') \
                and (project.is_collaborator(user)
                     or project.is_viewer(user)):
                pass
            else:

                raise PermissionDenied  # 403
        else:

            return redirect('/account/login/?next=%s'
                            % request.get_full_path())
    else:

        pass  # public project


    print '-----------------------------------------------------'
    print request.GET
    print request.POST
    print '-----------------------------------------------------'

    try:
        q = Q()
        for dep in dep_id:
            q = q | Q(ID = str(dep))
        deps = project.get_deployments().filter(q)
    except ObjectDoesNotExist:
        raise Http404

    print 'in index, deps ', deps
    context = get_context(request, deps, deps)

    nav_options = get_nav_options(request)
    context['nav_options'] = nav_options
    context['project'] = project
    
    context['target_name'] = []
    context['transmitter_frequency'] = []
    for i in range(len(dep_id)):
        target = deps[i].targetID
        target_name = target.name

        transmitter = deps[i].txID
        transmitter_frequency = transmitter.frequency

        context['target_name'].append(target_name)
        context['transmitter_frequency'].append(transmitter_frequency)

    return render(request, 'map/index.html', context)
    
def get_data(request, project_id):
    dep_id = request.GET['deployment']; 
    dep_id = dep_id.split(" ")
    dep_id = [int(i) for i in dep_id]
    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
        raise Http404
    if not project.is_public:
        if request.user.is_authenticated():
            user = request.user
            if project.is_owner(user) \
                or user.has_perm('project.can_view') \
                and (project.is_collaborator(user)
                     or project.is_viewer(user)):

                q = Q()
                for dep in dep_id:
                    q = q | Q(ID = str(dep))
                deps = project.get_deployments().filter(q)
            else:
                raise PermissionDenied  # 403
        else:

            return redirect('/account/login/?next=%s'
                            % request.get_full_path())
    else:
        try:
            q = Q()
            for dep in dep_id:
                q = q | Q(ID = str(dep))
            deps = project.get_deployments().filter(q)
        except ObjectDoesNotExist:
            raise Http404

    print 'in get_data about to get_context, deps is', deps
    context = get_context(request, deps, deps)
    print '-----------------------------'
    #print context['pos_data']
    print '-----------------------------'
    response = HttpResponse(json.dumps(context['pos_data']), content_type="application/json")
    return response

def get_latest_time(request, project_id, dep_id):
    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
        raise Http404

    if not project.is_public:
        if request.user.is_authenticated():
            user = request.user
            if project.is_owner(user) \
                or user.has_perm('project.can_view') \
                and (project.is_collaborator(user)
                     or project.is_viewer(user)):

                deps = project.get_deployments().filter(ID=dep_id)
            else:
                raise PermissionDenied  # 403
        else:

            return redirect('/account/login/?next=%s'
                            % request.get_full_path())
    else:

        deps = project.get_deployments().filter(ID=dep_id)

    context = get_context(request, deps, deps)
    # TODO: actually return the latest time
    response = HttpResponse("1234567", content_type="application/json")
    return response

## modify the script from here
def downloadKMLFile(request, project_id, dep_id, kml_type): 
  dep_id = dep_id.split("+")
  dep_id = [int(i) for i in dep_id]

  print kml_type
  trackPath='No'
  trackLocation='No'
  histogram='No'
  if ((kml_type=='trackOnly')|(kml_type=='track+point')|(kml_type=='track+histogram')|(kml_type=='allData')):
    trackPath='Yes'
  if ((kml_type=='pointOnly')|(kml_type=='track+point')|(kml_type=='point+histogram')|(kml_type=='allData')):
    trackLocation='Yes'
  if ((kml_type=='histogramOnly')|(kml_type=='track+histogram')|(kml_type=='point+histogram')|(kml_type=='allData')):
    histogram='Yes'

  try:
    project = Project.objects.get(ID=project_id)
  except ObjectDoesNotExist:
		raise Http404
      
  if not project.is_public:
    if request.user.is_authenticated():
      user = request.user
      if project.is_owner(user)\
           or (user.has_perm("project.can_view")
               and (project.is_collaborator(user)
                    or project.is_viewer(user))):
        q = Q()
        for dep in dep_id:
            q = q | Q(ID = str(dep))
        deps = project.get_deployments().filter(q)
      else:
        raise PermissionDenied #403

    else:
			return redirect("/auth/login/?next=%s" % request.get_full_path())


  else:
    q = Q()
    for dep in dep_id:
        q = q | Q(ID = str(dep))
    deps = project.get_deployments().filter(q)
  
  context = get_context(request, deps, deps)

  depTargetNames = []
  for dep in deps:
    depTargetNames.append(dep.targetID.name)

  response = HttpResponse(content_type='application/vnd.google-earth.kml+xml')
  response['Content-Disposition'] = ('attachement; filename="Deployment%s%s.kml"' % (map(str,depTargetNames),kml_type)).replace("'","")

  timeArray=[] 
  latitudeArray=[] 
  longitudeArray=[]
  for dep in json.loads(context['pos_data']):
      for row in dep:
        timeArray.append(row[2]) 
        latitudeArray.append(row[8][0])
        longitudeArray.append(row[8][1])

  kmlDoc = kmlGeneratorModule.main(depTargetNames, trackPath, trackLocation, histogram, timeArray, latitudeArray, longitudeArray)
  response.write(kmlDoc)
  return response

def download_by_dep(request, project_id, dep_id):
    dep_id = dep_id.split("+")
    dep_id = [int(i) for i in dep_id]

    try:
        project = Project.objects.get(ID=project_id)
    except ObjectDoesNotExist:
        raise Http404

    if not project.is_public:
        if request.user.is_authenticated():
            user = request.user
            if project.is_owner(user) \
                or user.has_perm('project.can_view') \
                and (project.is_collaborator(user)
                     or project.is_viewer(user)):
                try:
                    q = Q()
                    for dep in dep_id:
                        q = q | Q(ID = str(dep))
                    deps = project.get_deployments().filter(q)
                except ObjectDoesNotExist:
                    raise Http404
            else:
                raise PermissionDenied  # 403
        else:

            return redirect('/account/login/?next=%s'
                            % request.get_full_path())
    else:
        try:
            q = Q()
            for dep in dep_id:
                q = q | Q(ID = str(dep))
            deps = project.get_deployments().filter(q)
        except ObjectDoesNotExist:
            raise Http404

    context = get_context(request, deps, deps)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachement; filename="position_dep%s.csv"' % dep_id

    writer = csv.writer(response)
    writer.writerow([
        'ID',
        'deploymentID',
        'timestamp',
        'easting',
        'northing',
        'zone',
        'datetime',
        'latitude',
        'longitude',
        'likelihood',
        'activity',
        ])
    for dep in json.loads(context['pos_data']):
        for row in dep:
            writer.writerow([
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                str(row[5]) + row[9],
                row[10],
                row[8][0],
                row[8][1],
                row[6],
                row[7],
                ])
    return response


def view_by_target(request, target_id):
    ''' Compile a list of deployments associated with `target_id`. '''

    return HttpResponse('Not implemented yet. (targetID=%s)'
                        % target_id)


def view_by_tx(request, tx_id):
    ''' Compile a list of deployments associated with `tx_id`. '''

    return HttpResponse('Not implemented yet. (txID=%s)' % tx_id)

# TODO: Fix timezone/datetime things with the new functions in utils if we extend these graphs
@login_required(login_url='account/login')
def system_status(
    request,
    static_field='siteID',
    obj='telemetry',
    excluded_fields=['ID', 'siteID', 'timestamp', 'datetime', 'timezone'
                     ],
    ):

    if request.GET.get('start_date'):
        start_date = request.GET.get('start_date')
    else:
        start_date = (datetime.datetime.now()
                      - datetime.timedelta(1)).strftime('%m/%d/%Y %H:%M:%S'
                )

    model_obj = rest_api.get_model_type(obj)
    obj_fields_keys = [field.name for field in model_obj._meta.fields
                       if field.name not in excluded_fields]
    static_field_values = model_obj.objects.values_list(static_field,
            flat=True).distinct()
    fields = copy.copy(request.GET.getlist('field'))

    # Replaces field's name for selected field's value

    sel_static_values = request.GET.getlist('filter_field')
    for sel_values in sel_static_values:
        (key, value) = sel_values.split(',')
        fields[fields.index(key)] = sel_values

    content = {}
    content = dict(
        nav_options=get_nav_options(request),
        fields=json.dumps(fields),
        static_field_values=static_field_values,
        obj_fields_keys=obj_fields_keys,
        start_date=start_date,
        static_field=json.dumps(static_field),
        )

    try:
        data = rest_api.get_model_data(request)
    except Exception, e:
        print e
        content['data'] = json.dumps(None)
    else:
        content['data'] = json.dumps(rest_api.json_parse(data),
                cls=utils.DateTimeEncoder)

    return render(request, 'map/system_status.html', content)


@login_required(login_url='account/login')
def est_status(
    request,
    static_field='deploymentID',
    obj='est',
    excluded_fields=['ID', 'deploymentID', 'siteID', 'timestamp'],
    ):

    if request.GET.get('start_date'):
        start_date = request.GET.get('start_date')
    else:
        start_date = (datetime.datetime.now()
                      - datetime.timedelta(1)).strftime('%m/%d/%Y %H:%M:%S'
                )

    model_obj = rest_api.get_model_type(obj)
    obj_fields_keys = [field.name for field in model_obj._meta.fields
                       if field.name not in excluded_fields]
    static_field_values = model_obj.objects.values_list(static_field,
            flat=True).distinct()
    fields = copy.copy(request.GET.getlist('field'))

    # Replaces field's name for selected field's value

    sel_static_values = request.GET.getlist('filter_field')
    for sel_values in sel_static_values:
        (key, value) = sel_values.split(',')
        fields[fields.index(key)] = sel_values

    content = {}
    content = dict(
        nav_options=get_nav_options(request),
        fields=json.dumps(fields),
        static_field_values=static_field_values,
        obj_fields_keys=obj_fields_keys,
        start_date=start_date,
        static_field=json.dumps(static_field),
        )

    try:
        data = rest_api.get_model_data(request)
    except Exception, e:
        print e
        content['data'] = json.dumps(None)
    else:
        content['data'] = json.dumps(rest_api.json_parse(data),
                cls=utils.DateTimeEncoder)

    return render(request, 'map/est_status.html', content)


@login_required(login_url='/account/login')
def generic_graph(
    request,
    objs=['telemetry', 'position', 'deployment', 'est'],
    excluded_fields=['siteID', 'datetime', 'timezone', 'utm_zone_number'
                     , 'utm_zone_letter'],
    template='map/generic_graph.html',
    ):

    nav_options = get_nav_options(request)
    content = {}
    content = dict(
        objs=objs,
        nav_options=nav_options,
        excluded_fields=json.dumps(excluded_fields),
        selected_obj=json.dumps(request.GET.get('obj')),
        offset=request.GET.get('offset'),
        n_items=request.GET.get('n_items'),
        )

    fields = request.GET.getlist('field')
    content['fields'] = json.dumps(fields)

    try:
        data = rest_api.get_model_data(request)
    except Exception, e:
        print e
        content["data"] = json.dumps(None)
    else:
        content["data"] = json.dumps(rest_api.json_parse(data), cls=DateTimeEncoder)

    return render(request, template, content)
