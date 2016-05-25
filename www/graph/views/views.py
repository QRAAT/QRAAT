import json
import utils
import rest_api
from django.db.models import Q, Avg
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
from project.models import Site, Telemetry, Est, Deployment
from graph.forms import TelemetryGraphForm, EstGraphForm, ProcessingGraphForm
from viewsutils import get_nav_options #TODO: change from ___

import time
import datetime
from calendar import timegm
from itertools import chain

FIELD_TYPE = {
     0: 'DECIMAL', #
     1: 'TINY',
     2: 'SHORT', #
     3: 'LONG', #
     4: 'FLOAT', #
     5: 'DOUBLE', #
     6: 'NULL',
     7: 'TIMESTAMP',
     8: 'LONGLONG', #
     9: 'INT24',
     10: 'DATE',
     11: 'TIME',
     12: 'DATETIME',
     13: 'YEAR',
     14: 'NEWDATE',
     15: 'VARCHAR', #
     16: 'BIT',
     246: 'NEWDECIMAL', #
     247: 'INTERVAL',
     248: 'SET',
     249: 'TINY_BLOB',
     250: 'MEDIUM_BLOB',
     251: 'LONG_BLOB',
     252: 'BLOB',
     253: 'VAR_STRING', #
     254: 'STRING', #
     255: 'GEOMETRY'
}




def graph_home(request):

    nav_options = get_nav_options(request)

    try:
        return render(request, "graph/graph_home.html", {'nav_options': nav_options})
    except:
        return HttpResponse("Sorry, the graph home page didn't render correctly.") # what type of response should this be?


def get_graphs_context(request):
    # get graph parameters from request/query
    site_names = request.GET.getlist('site_names', "all") # what is the expected behavior if no sites are given?

    # user can enter time interval in a variety of ways
    start_timestamp = request.GET.get('start_timestamp', None)  
    end_timestamp = request.GET.get('end_timestamp', None)
    datetime_from = request.GET.get('datetime_start', None)
    datetime_to = request.GET.get('datetime_end', None)
    interval = request.GET.get('interval', None)

    move_interval = request.GET.get('move_interval', None)

    graph_variables = request.GET.getlist('graph_variables', None) # variables to plot
    
    # make a list of site names from user
    if (site_names[0]).lower() != "all":
        sites = Site.objects.filter(name__in = site_names) # query to get Site objects associated with sites names from user
    else:
        sites = Site.objects.all() # query to get all Site objects
    
    site_IDs = []
    sites_dict = {}
    for i in range(len(sites)):
        site_IDs.append(int(sites[i].ID))
        site_ASCII_name = str(sites[i].name).capitalize() #convert site_names from Unicode to ASCII strings
        site_ASCII_name = site_ASCII_name[:4] + " " + site_ASCII_name[4:]
        sites_dict[int(sites[i].ID)] = site_ASCII_name #can lookup site.name by site.ID
    
    start_timestamp, end_timestamp, update_form_time = set_time_parameters(start_timestamp, end_timestamp, datetime_from, datetime_to, interval, move_interval)
    
    if ((start_timestamp==0) and (end_timestamp==0)):
        return HttpResponseBadRequest("Please double check your date/time values.") # this doesn't work - what to do instead?

    for i in range(len(graph_variables)):
        graph_variables[i] = str(graph_variables[i]) #convert graph_variables from Unicode to ASCII strings

    context = {
        'sites': sites_dict,
        'site_IDs': site_IDs, #used in query
        'graph_variables': graph_variables,
        'start_timestamp': start_timestamp, #used in query
        'end_timestamp': end_timestamp, #used in query
        'update_form_time': update_form_time
    }
    print 'bybye'
    print context['start_timestamp']
    print context['end_timestamp']
    
    return context


# Based on the time format (which two values user supplies), fill in the other 
def fix_time(start_timestamp, end_timestamp, datetime_from, datetime_to, interval):
    pass
"""Used by telemetry_graphs() to set start_timestamp and end_timestamp before querying the database"""
def set_time_parameters(start_timestamp, end_timestamp, datetime_from, datetime_to, interval, move_interval):

    # dictionary used to update time fields in form submited with back or forward buttons
    update_form_time = {}
    update_form_time['datetime_start'] = None
    update_form_time['datetime_end'] = None
    update_form_time['start_timestamp'] = None
    update_form_time['end_timestamp'] = None

    # A good URL has start and end_timestamp filled in.
    # If not, we proceed through a hiearchy to determine the time to use
    if start_timestamp and end_timestamp:
        update_form_time['start_timestamp'] = start_timestamp
        start_timestamp = int(start_timestamp)
        update_form_time['end_timestamp'] = end_timestamp
        end_timestamp = int(end_timestamp)

    else:
        # data type conversions
        if start_timestamp:
            update_form_time['start_timestamp'] = start_timestamp
            start_timestamp = int(start_timestamp)
        if end_timestamp:
            update_form_time['end_timestamp'] = end_timestamp
            if end_timestamp.lower() == "now":
                    end_timestamp = int(time.time()) # set end_timestamp to now
            else:
                    end_timestamp = int(end_timestamp)
        if interval:
            interval = int(interval)
        if datetime_to.lower() == "now":
            datetime_to = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # set datetime_to to current datetime
                            
        # datetime format trumps UNIX timestamp format if both are given
        # datetimes
        if datetime_from and datetime_to:
            start_timestamp = utils.datelocal_totimestamp(utils.strptime(datetime_from, '%Y-%m-%d %H:%M:%S'))
            end_timestamp = utils.datelocal_totimestamp(utils.strptime(datetime_to, '%Y-%m-%d %H:%M:%S'))

        elif datetime_from and interval:
            update_form_time['datetime_start'] = datetime_from
            start_timestamp = utils.datelocal_totimestamp(utils.strptime(datetime_from, '%Y-%m-%d %H:%M:%S'))
            end_timestamp = start_timestamp + interval

        elif datetime_to and interval:
            update_form_time['datetime_end'] = datetime_to
            end_timestamp = utils.datelocal_totimestamp(utils.strptime(datetime_to, '%Y-%m-%d %H:%M:%S'))
            start_timestamp = end_timestamp - interval

        # UNIX timestamps
        elif start_timestamp and end_timestamp:
            pass
        
        elif start_timestamp and interval:
            end_timestamp = start_timestamp + interval

        elif end_timestamp and interval:
            start_timestamp = end_timestamp - interval

        else:
            return (0,0)
            #return HttpResponseBadRequest("Please double check your date/time values.") # this doesn't work - what to do instead?

    # back or forward buttons
    interval = end_timestamp - start_timestamp # TOOD: get rid of and interval once i determine how interval is taken care of
    if move_interval and interval:
        if move_interval == 'back':
            start_timestamp -= interval
            end_timestamp -= interval
        elif move_interval == 'forward':
            start_timestamp += interval
            end_timestamp += interval

        if update_form_time['start_timestamp'] and update_form_time['end_timestamp']:
            update_form_time['start_timestamp'] = start_timestamp
            update_form_time['end_timestamp'] = end_timestamp
            print 'hihihi'
            print update_form_time['start_timestamp']
            print update_form_time['end_timestamp'] 
        else:
            if update_form_time['datetime_start'] and interval:
                update_form_time['datetime_start'] = datetime.datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            elif update_form_time['datetime_end'] and interval:
                update_form_time['datetime_end'] = datetime.datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            elif update_form_time['start_timestamp'] and interval:
                update_form_time['start_timestamp'] = start_timestamp
            elif update_form_time['end_timestamp'] and interval:
                update_form_time['end_timestamp'] = end_timestamp

    return (start_timestamp, end_timestamp, update_form_time)


def create_data_list_from_QuerySet(query_results, requested_fields):
    data = []
    for row in query_results:
        row_dict = {}
        for attr in requested_fields:
            try:
                row_dict[attr] = float(getattr(row,attr)) # general case must be float not int
            except:
                row_dict[attr] = str(getattr(row,attr))

        row_dict['timestamp'] = int(row.timestamp)
        row_dict['siteID'] = int(row.siteID.ID) # always needed to determine which site data point is for # better way to do this? # will all possible graph types have a siteID associated with the data rows??

        data.append(row_dict)
    
    return data


def create_data_list_from_dict(query_results, requested_fields): #remove table_name
    data = []
    for row in query_results:
        row_dict = {}
        for attr in requested_fields:
            try:
                row_dict[attr] = float(row[attr]) # general case must be float not int
            except:
                row_dict[attr] = str(row[attr])

        row_dict['timestamp'] = int(row["timestamp"])
        row_dict['siteID'] = int(row["siteID"]) # always needed to determine which site data point is for # better way to do this? # will all possible graph types have a siteID associated with the data rows??

        data.append(row_dict)
    
    return data


def update_form_time_and_date(requestGET, context):
    # used to change the time/date in requested form
    update_form_time = context['update_form_time']

    if update_form_time['datetime_start']:
        requestGET['datetime_start'] = update_form_time['datetime_start']
    elif update_form_time['datetime_end']:
        requestGET['datetime_end'] = update_form_time['datetime_end']
    elif update_form_time['start_timestamp']:
        requestGET['start_timestamp'] = update_form_time['start_timestamp']
    elif update_form_time['end_timestamp']:
        requestGET['end_timestamp'] = update_form_time['end_timestamp']

    return requestGET

# Like above but copies all values. TODO: If I make similar changes (display two date time fields at a time, have timestamp be the canonical format sent in the GET request) to the non-telemetry graph pages, maybe remove the above
def update_all_form_time_and_date(requestGET, context):
    # used to change the time/date in requested form
    update_form_time = context['update_form_time']

    if update_form_time['datetime_start']:
        requestGET['datetime_start'] = update_form_time['datetime_start']
    if update_form_time['datetime_end']:
      requestGET['datetime_end'] = update_form_time['datetime_end']
    if update_form_time['start_timestamp']:
      requestGET['start_timestamp'] = update_form_time['start_timestamp']
    if update_form_time['end_timestamp']:
        requestGET['end_timestamp'] = update_form_time['end_timestamp']

    return requestGET


def telemetry_graphs(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    nav_options = get_nav_options(request)

    if not request.GET: # no parameters from user yet
        try:
            #telemetry_graph_form = TelemetryGraphForm() # unbound form - uses default initial form values
            #return render(request, "graph/telemetry_graphs_form.html", {'nav_options': nav_options, 'form': telemetry_graph_form})
            end_timestamp = int(time.time())
            start_timestamp = end_timestamp - 18000 # 5 hour interval
            response = redirect("graph:telemetry_graphs")
            query_str = "?date_format=sts_i&start_timestamp={}&end_timestamp={}&graph_variables=all&site_names=all".format(start_timestamp, end_timestamp)
            response['Location'] += query_str
            return response
        except:
                return HttpResponseBadRequest("Sorry, something went wrong when trying to load the Telemetry Graphs page.")

    else: # user has already filled out the form or entered parameters via the URL
        requestGET = request.GET.copy()
       
        context = get_telemetry_graphs_context(request) # gets all the info from URL, runs query, formats data
        print 'in telemetry_graphs'
        print context['start_timestamp']
        print context['end_timestamp']

        requestGET = update_all_form_time_and_date(requestGET, context)
        print requestGET['start_timestamp']
        print requestGET['end_timestamp']
        
        telemetry_graph_form = TelemetryGraphForm(data = requestGET)

        context['nav_options'] = nav_options
        context['form'] = telemetry_graph_form
    
        return render(request, "graph/telemetry_graphs.html", context)


def get_telemetry_graphs_context(request):
    context = get_graphs_context(request)

    graph_variables = context["graph_variables"]

    if (graph_variables[0]).lower() == "all":
        graph_variables = ['intemp', 'extemp', 'voltage', 'siteID', 'ping_power', 'ping_computer', 'site_status']
    
    for i in range(len(graph_variables)):
        graph_variables[i] = str(graph_variables[i]) #convert graph_variables from Unicode to ASCII strings

    # query the database for the data
    #select avg(intemp) as intemp_avg, avg(extemp) as extemp_avg, avg(voltage) as voltage_avg, avg(ping_power) as ping_power_avg, avg(ping_computer) as ping_computer_avg, avg(site_status) as site_status_avg from telemetry where timestamp >= 1371408002 and timestamp <= 1371408602 group by siteID order by siteID;
    query_results = Telemetry.objects.filter(siteID__in = context["site_IDs"]).filter(timestamp__gte = context["start_timestamp"]).filter(timestamp__lte = context["end_timestamp"]).order_by('timestamp')
    data = create_data_list_from_QuerySet(query_results, graph_variables) #doesn't work because Flot needs numbers not strings?

    min_range_lookup_dict = {
        'intemp': 0,
        'extemp': 0,
        'voltage': 9,
        'site_status': 0
    }
    
    max_range_lookup_dict = {
        'intemp': 60,
        'extemp': 60,
        'voltage': 15,
        'site_status': 6
    }

    units_lookup_dict = {
        'intemp': "C",
        'extemp': "C",
        'voltage': "V"
    }

    context['graph_data'] = json.dumps(data)
    context['min_plot_range_lookup'] = min_range_lookup_dict
    context['max_plot_range_lookup'] = max_range_lookup_dict
    context['units_lookup_dict'] = units_lookup_dict
    context['graph_variables'] = graph_variables # because they've been updated

    return context


def est_graphs(request):
    nav_options = get_nav_options(request)
    
    if not request.GET: # no parameters from user yet
        try:
            est_graph_form = EstGraphForm() # unbound form - uses default initial form values
            return render(request, "graph/est_graphs_form.html", {'nav_options': nav_options, 'form': est_graph_form})
        except:
            return HttpResponseBadRequest("Sorry, something went wrong when trying to load the Est Graphs page.")

    else: # user has already filled out the form or entered parameters via the URL
        requestGET = request.GET.copy()

        #context = get_graphs_context(request) # gets all the info from URL, runs query, formats data      
        context = get_est_graphs_context(request) # gets all the info from URL, runs query, formats data

        requestGET = update_form_time_and_date(requestGET, context)
        est_graph_form = EstGraphForm(data = requestGET)

        context['nav_options'] = nav_options
        context['form'] = est_graph_form

        return render(request, "graph/est_graphs.html", context)


def get_est_graphs_context(request):
    context = get_graphs_context(request)
    
    deployment_ID = int(request.GET.get('deployment_id', None))
                  
    graph_variables = context["graph_variables"]

    for i in range(len(graph_variables)):
        graph_variables[i] = str(graph_variables[i]) #convert graph_variables from Unicode to ASCII strings
                                                  
    query_results = Est.objects.filter(siteID__in = context["site_IDs"]).filter(deploymentID = deployment_ID).filter(timestamp__gte = context["start_timestamp"]).filter(timestamp__lte = context["end_timestamp"]).order_by('timestamp')
    data = create_data_list_from_QuerySet(query_results, graph_variables) #doesn't work because Flot needs numbers not strings?\

    # add parameters to context dictionary
    context['graph_data'] = json.dumps(data)
    context['min_plot_range_lookup'] = {}
    context['max_plot_range_lookup'] = {}
    context['units_lookup_dict'] = {}
    context['graph_variables'] = graph_variables # they've been updated
    context['deployment_ID'] = deployment_ID # why?

    return context


def processing_graphs(request):

    nav_options = get_nav_options(request)
    
    if not request.GET: # no parameters from user yet
        try:
                processing_graph_form = ProcessingGraphForm() # unbound form - uses default initial form values
                return render(request, "graph/processing_graphs_form.html", {'nav_options': nav_options, 'form': processing_graph_form})
        except:
                return HttpResponseBadRequest("Sorry, something went wrong when trying to load the Processing Graphs page.")

    else: # user has already filled out the form or entered parameters via the URL
        requestGET = request.GET.copy()
        
        context = get_processing_graphs_context(request) # gets all the info from URL, runs query, formats data
        
        requestGET = update_form_time_and_date(requestGET, context)
        processing_graph_form = ProcessingGraphForm(data = requestGET)
        
        context['nav_options'] = nav_options
        context['form'] = processing_graph_form

        return render(request, "graph/processing_graphs.html", context)


def get_processing_graphs_context(request):   
    context = get_graphs_context(request)

    graph_variables = context['graph_variables']
    for i in range(len(graph_variables)):
        graph_variables[i] = str(graph_variables[i]) #convert graph_variables from Unicode to ASCII strings

    site_IDs_for_query = str(context["site_IDs"])
    site_IDs_for_query = "(" + site_IDs_for_query[1:-1] +")"

    cursor = connection.cursor()

    # query for "estserver"
    procount_query = "SELECT * FROM qraat.procount WHERE timestamp >= " + str(context['start_timestamp']) + " AND timestamp <= " + str(context['end_timestamp']) + " AND siteID in " + site_IDs_for_query
    cursor.execute(procount_query)
    procount_query_results = dictfetchall(cursor) # HELP - is this OK?
    procount_data = create_data_list_from_dict(procount_query_results, ["timestamp" , "siteID", "estserver"])

    #query for "server_det" and "site_det"
    detcount_query = "SELECT * FROM qraat.detcount WHERE timestamp >= " + str(context['start_timestamp']) + " AND timestamp <= " + str(context['end_timestamp']) + " AND siteID in " + site_IDs_for_query
    cursor.execute(detcount_query)
    detcount_query_results = dictfetchall(cursor) # HELP - is this OK?
    detcount_data = create_data_list_from_dict(detcount_query_results, ["timestamp" , "siteID", "server", "site"])

    data = list(chain(procount_data, detcount_data)) # combine procount and detcount query results

    context['graph_data'] = json.dumps(data)
    context['min_plot_range_lookup'] = {}
    context['max_plot_range_lookup'] = {}
    context['units_lookup_dict'] = {}
    context['graph_variables'] = graph_variables # they've been updated

    return context


def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict. Taken from the official Django documentation and tutorials"""
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]
