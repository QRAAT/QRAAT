import json
import utils
import rest_api
import os
import sys
import copy
from collections import OrderedDict
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
from project.models import Site, Deployment
from graph.forms import DashboardForm
from viewsutils import get_nav_options #TODO: change from ___

import time
import datetime
from calendar import timegm

def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict. Taken from the official Django documentation and tutorials"""
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

# >>>>>> new code starting here <<<<<<
class LastUpdatedOrderedDict(OrderedDict):
    'Store items in the order the keys were last added'

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)

def dashboard_page(request):
    nav_options = get_nav_options(request)
    context = {}
    
    if not request.GET: # no parameters from user yet
        try:
            dashboard_page = DashboardForm() # unbound form - uses default initial form values
            return render(request, "graph/dashboard.html", {'nav_options': nav_options, 'form': dashboard_page})
        except:
            return HttpResponseBadRequest("Sorry, something went wrong when trying to load the dashboard page.")

    else: # user has already filled out the form or entered parameters via the URL
        requestGET = request.GET.copy()
        
        context = get_context_for_all(request)
        requestGET['datetime_start'] = str(context['datetime_start'])

        dashboard_page = DashboardForm(data = requestGET)
        context['form'] = dashboard_page
        context['nav_options'] = nav_options
        return render(request, "graph/dashboard.html", context)

def get_context_for_all(request):
    
    context = get_interval_and_start_time(request)

    table_sites = request.GET.getlist('info_sites')
    if len(table_sites) > 0 and table_sites[0].lower() == 'all':
        table_sites = ['telemetry', 'detcount', 'estcount', 'timecheck']
    #print 'aqui: ' + str(table_sites)
    table_deployments = request.GET.getlist('info_deployments')
    if len(table_deployments) > 0 and table_deployments[0].lower() == 'all':
        table_deployments = ['est', 'bearing', 'position', 'track_pos']
    
    table_system = request.GET.getlist('info_system')
    if len(table_system) > 0 and table_system[0].lower() == 'all':
        table_system = ['processing_statistics', 'processing_cursor']
    
    data_sites = get_data_for_tables(table_sites, context['start_timestamp'], context['interval'], context['colors'])
    data_deployments = get_data_for_tables_deployment(table_deployments, context['start_timestamp'], context['interval'], context['colors'])
    data_system = get_data_for_tables_system(table_system, context['start_timestamp'], context['interval'], context['colors'])

    context['data_sites'] = data_sites
    context['data_deployments'] = data_deployments
    context['data_system'] = data_system
    
    return context

def get_interval_and_start_time(request):
    context = {}
    context = get_names_for_all_column_headers()

    move_interval = request.GET.get('move_interval', None)
    datetime_start = request.GET.get('datetime_start', None)
    interval = request.GET.get('interval', None)

    if not interval:
        interval = 10*60 #defaul interval is 10 minutes
    else:
        interval = int(interval)*60 #converting minutes (more suitable) to seconds
    
    if not datetime_start or datetime_start.lower() == 'now':
        datetime_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    start_timestamp = timegm(time.strptime(datetime_start, '%Y-%m-%d %H:%M:%S')) + 7*60*60 # used to get PDT to UTC - fix this - talk with Marcel

    if move_interval and move_interval == 'back':
        start_timestamp -= interval
    elif move_interval and move_interval == 'forward':
        start_timestamp += interval
    
    try:
        datetime_start = datetime.datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass # value out of range

    context['datetime_start'] = datetime_start
    context['start_timestamp'] = start_timestamp
    context['interval'] = interval
    return context

def get_data_for_tables(tables, start_timestamp, interval, colors):
    data = LastUpdatedOrderedDict()
    cursor = connection.cursor()

    for table in tables:
        query = ""
        if not table in data:
            data[table] = LastUpdatedOrderedDict()
        if table == 'telemetry':
            query = "SELECT siteID, ROUND(AVG(intemp),3) AS intemp, ROUND(AVG(extemp),3) AS extemp, ROUND(AVG(voltage),3) AS voltage, ROUND(AVG(ping_power),3) AS avg_ping_power, ROUND(AVG(ping_computer),3) AS avg_ping_computer, (select ping_power from qraat.telemetry as teleIN where teleIN.siteID = teleOUT.siteID and timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " order by timestamp desc limit 1) AS last_ping_power, (select ping_computer from qraat.telemetry as teleIN where teleIN.siteID = teleOUT.siteID and timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " order by timestamp desc limit 1) AS last_ping_computer, (select site_status from qraat.telemetry as teleIN where teleIN.siteID = teleOUT.siteID and timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " order by timestamp desc limit 1) AS site_status FROM qraat.telemetry AS teleOUT WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID"
        elif table == 'detcount':
            query = "SELECT siteID, ROUND(AVG(server),3) AS server, ROUND(AVG(site),3) AS site FROM qraat.detcount WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID"
        elif table == 'estcount':
            query = "SELECT siteID, ROUND(AVG(server),3) AS server FROM qraat.estcount WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID"
        elif table == 'timecheck':
            query = "SELECT siteID, ROUND(AVG(time_offset),3) AS time_offset FROM qraat.timecheck WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID"
        
        try:
            cursor.execute(query)
            query_results = dictfetchall(cursor)
            data[table] = create_data_map_ordered_by_site(query_results, 'siteID', colors)
        except:
            pass #query is empty
    
    return data

def get_data_for_tables_deployment(tables, start_timestamp, interval, colors):
    
    threshold = os.environ['RMG_POS_EST_THRESHOLD']

    data = LastUpdatedOrderedDict()
    cursor = connection.cursor()
    
    for table in tables:
        queries = {}
        query_results = {}
        if not table in data:
            data[table] = LastUpdatedOrderedDict()

        # this query would be used if fields time_start and time_end work properly
        #deploy_query = "deploymentID in (SELECT ID FROM qraat.deployment WHERE time_start IS NOT NULL AND time_end IS NULL AND ((" + str(start_timestamp-interval) + " <= time_start AND " + str(start_timestamp) + " >= time_start) OR (" + str(start_timestamp-interval) + " >= time_start))) AND"
        deploy_query = "deploymentID IN (SELECT distinct deploymentID FROM qraat.est WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + ")"

        if table == "est":
            queries['est_records'] = "SELECT siteID, deploymentID, COUNT(*) AS est_records FROM qraat.est WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID, deploymentID ORDER BY siteID"
            queries['est_true_positives'] = "SELECT siteID, deploymentID, COUNT(*) AS est_true_positives FROM qraat.est WHERE qraat.est.ID IN (SELECT estID FROM qraat.estscore WHERE score >= " + threshold + ") AND timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID, deploymentID ORDER BY siteID"
            queries['est_false_positives'] = "SELECT siteID, deploymentID, COUNT(*) AS est_false_positives FROM qraat.est WHERE qraat.est.ID IN (SELECT estID FROM qraat.estscore WHERE score < " + threshold + ") AND timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID, deploymentID ORDER BY siteID"
            queries['est_perceived_pulse_rate'] = "SELECT siteID, deploymentID, ROUND(AVG(pulse_interval),3) AS est_perceived_pulse_rate FROM qraat.estinterval WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " AND " + deploy_query + " GROUP BY siteID, deploymentID ORDER BY siteID"
            queries['est_snr'] = "SELECT siteID, deploymentID, ROUND(AVG(edsnr),3) AS est_snr FROM qraat.est WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY siteID, deploymentID ORDER BY siteID"
            
            for variable, query in queries.items():
                cursor.execute(query)
                query_results[variable] = dictfetchall(cursor)
            
            data[table] = create_data_map_for_est(query_results, interval, colors)
            
        elif table == "bearing":
            query = "SELECT deploymentID, siteID, COUNT(*) AS num_of_bearings, ROUND(AVG(bearing),3) AS current_bearing, ROUND(AVG(likelihood),3) AS bearing_likelihood, ROUND(AVG(activity),3) AS bearing_activity FROM qraat.bearing WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " AND " + deploy_query + " GROUP BY deploymentID, siteID ORDER BY deploymentID"
            cursor.execute(query)
            query_results = dictfetchall(cursor)
            data[table] = create_data_map_for_bearing(query_results, colors)
        elif table == "position":
            query = "SELECT deploymentID, COUNT(*) AS num_of_pos, ROUND(AVG(likelihood),3) AS position_likelihood, ROUND(AVG(activity),3) AS position_activity, ROUND(AVG(easting),3) AS easting, ROUND(AVG(northing),3) AS northing FROM qraat.position WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " AND " + deploy_query + " GROUP BY deploymentID ORDER BY deploymentID"
            cursor.execute(query)
            query_results = dictfetchall(cursor)
            data[table] = create_data_map_by_deployment(query_results, table, colors)
        elif table == "track_pos":
            query = "SELECT deploymentID, COUNT(*) AS num_of_track_pos FROM qraat.track_pos WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " AND " + deploy_query + " GROUP BY deploymentID ORDER BY deploymentID"
            cursor.execute(query)
            query_results = dictfetchall(cursor)
            data[table] = create_data_map_by_deployment(query_results, table, colors)

    return organize_data_before_send_to_html(data)

def get_data_for_tables_system(tables, start_timestamp, interval, colors):
    data = LastUpdatedOrderedDict()
    cursor = connection.cursor()

    for table in tables:
        if table == "processing_statistics":
            query = "SELECT process, SUM(number_records_input) AS number_records_input, SUM(number_records_output) AS number_records_output, ROUND((SUM(number_records_output)/SUM(duration)),3) AS output_processing_rate FROM qraat.processing_statistics WHERE timestamp >= " + str(start_timestamp-interval) + " AND timestamp <= " + str(start_timestamp) + " GROUP BY process"
            cursor.execute(query)
            query_results = dictfetchall(cursor)
            data[table] = create_data_map_for_processing_statistics(query_results)
        elif table == "processing_cursor":
            query = "SELECT name, value FROM qraat.processing_cursor";
            cursor.execute(query)
            query_results = dictfetchall(cursor)
            
            query = "SELECT MAX(ID) AS max_est_id FROM qraat.est";
            cursor.execute(query)
            max_est_id_results = dictfetchall(cursor)

            query = "SELECT MAX(ID) AS max_pos_id FROM qraat.position";
            cursor.execute(query)
            max_pos_id_results = dictfetchall(cursor)

            data[table] = create_data_map_for_processing_cursor(query_results, max_est_id_results, max_pos_id_results)

    return data

def create_data_map_for_processing_cursor(query_results, max_est_id_results, max_pos_id_results):
    data = LastUpdatedOrderedDict()
    max_est_id = 0
    max_pos_id = 0
    try:
        max_est_id = int(max_est_id_results[0]['max_est_id'])
        max_pos_id = int(max_pos_id_results[0]['max_pos_id'])
    except:
        pass #something wrong on database

    for row in query_results:
        data[str(row['name'])] = LastUpdatedOrderedDict()
        data[str(row['name'])]['value'] = int(row['value'])
    
    for key, value in data.items():
        
        if key == 'position':
            data['position']['record_not_processed'] = max_est_id-value['value']
        elif key == 'track_pos':
            value['record_not_processed'] = max_pos_id-value['value']
        elif key == 'estscore':
            value['record_not_processed'] = max_est_id-value['value']


    return data

def create_data_map_for_processing_statistics(query_results):
    data = LastUpdatedOrderedDict()

    for row in query_results:
        if not str(row['process']) in data:
            data[str(row['process'])] = LastUpdatedOrderedDict()
        for key, value in row.items():
            if key == 'output_processing_rate':
                data[str(row['process'])][str(key)] = str(value)+' sec'
            elif key != 'process':
                if not str(key) in data[str(row['process'])]:
                    data[str(row['process'])][str(key)] = 0
                if type(value) == float:
                    data[str(row['process'])][str(key)] = float(value)
                else:
                    data[str(row['process'])][str(key)] = int(value)
    return data


def organize_data_before_send_to_html(data):
    new_data = LastUpdatedOrderedDict()
    for table in data:
        if table == 'est' or table == 'bearing':
            for depID, data_by_site in data[table].items():
                if not depID in new_data:
                    new_data[depID] = copy.deepcopy(data_by_site)
                else:
                    for siteID, data_by_variable in data_by_site.items():
                        if not siteID in new_data[depID]:
                            new_data[depID][siteID] = copy.deepcopy(data_by_variable)
                        else:
                            for variable, value in data_by_variable.items():
                                new_data[depID][siteID][variable] = value
        elif table == 'position':
            for depID, data_by_variable in data['position'].items():
                if not depID in new_data:
                    new_data[depID] = {}
                new_data[depID]['position'] = copy.deepcopy(data_by_variable)
        elif table == 'track_pos':
            for depID, data_by_variable in data['track_pos'].items():
                if not depID in new_data:
                    new_data[depID] = {}
                new_data[depID]['track_pos'] = copy.deepcopy(data_by_variable)

    return new_data

def create_data_map_by_deployment(query_results, table, colors):
    data = LastUpdatedOrderedDict()

    for row in query_results:
        for key, value in row.items():
            if not int(row['deploymentID']) in data:
                data[int(row['deploymentID'])] = LastUpdatedOrderedDict()
            if key != 'deploymentID' and key != 'easting' and key != 'northing':
                if key in colors:
                    for limit, color in colors[key].items():
                        if float(value) <= limit:
                            data[int(row['deploymentID'])][key] = (float(value), color)
                            break
                else:
                    data[int(row['deploymentID'])][key] = float(value)

            if table == 'position':
                data[int(row['deploymentID'])]['current_position'] = (float(row['easting']), float(row['northing']))
    return data

def create_data_map_for_bearing(query_results, colors):
    data = LastUpdatedOrderedDict()
    
    for row in query_results:
        for variable, value in row.items():
            if not int(row['deploymentID']) in data:
                data[int(row['deploymentID'])] = LastUpdatedOrderedDict()
            if not int(row['siteID']) in data[int(row['deploymentID'])]:
                data[int(row['deploymentID'])][int(row['siteID'])] = LastUpdatedOrderedDict()
            
            if variable != 'deploymentID' and variable != 'siteID' and not variable in data[int(row['deploymentID'])][int(row['siteID'])]:
                data[int(row['deploymentID'])][int(row['siteID'])][variable] = 0

                if variable in colors:
                    for limit, color in colors[variable].items():
                        if float(row[variable]) <= limit:
                            data[int(row['deploymentID'])][int(row['siteID'])][variable] = (float(row[variable]), color)
                            break
                else:
                    data[int(row['deploymentID'])][int(row['siteID'])][variable] = float(row[variable])

    return data


def create_data_map_for_est(query_results, interval, colors):
    data = LastUpdatedOrderedDict()
    
    for variable, query_result in query_results.items():
        for row in query_result:
            if not int(row['deploymentID']) in data:
                data[int(row['deploymentID'])] = LastUpdatedOrderedDict()
            if not int(row['siteID']) in data[int(row['deploymentID'])]:
                data[int(row['deploymentID'])][int(row['siteID'])] = LastUpdatedOrderedDict()
            if not variable in data[int(row['deploymentID'])][int(row['siteID'])]:
                data[int(row['deploymentID'])][int(row['siteID'])][variable] = 0

            if variable in colors:
                for limit, color in colors[variable].items():
                    if float(row[variable]) <= limit:
                        data[int(row['deploymentID'])][int(row['siteID'])][variable] = (float(row[variable]), color)
                        break
            else:
                data[int(row['deploymentID'])][int(row['siteID'])][variable] = float(row[variable])
                
    for siteID, data_by_site in data.items():
        for deploymentID, data_by_deployment in data_by_site.items():
            try:
                data[siteID][deploymentID]['total'] = interval / data_by_deployment['perceived_pulse_rate']
                data[siteID][deploymentID]['misses'] = "{:.2f}".format(data[siteID][deploymentID]['total'] - data_by_deployment['true_positives']) #"{:.2f}".format()
                data[siteID][deploymentID]['total'] = "{:.2f}".format(data[siteID][deploymentID]['total'])
            except:
                pass #there isn't pulse_perceived_rate returned by the query

    return data


def create_data_map_ordered_by_site(query_results, order_by, colors):
    data = LastUpdatedOrderedDict()
    
    for row in query_results:
        row_dict = {}
        if not int(row[order_by]) in data:
            data[int(row[order_by])] = LastUpdatedOrderedDict()
        for key, value in row.items():
            if key != order_by:
                if value != None:
                    for var, limits in colors.items():
                        if var == key:
                            for limit, color in limits.items():
                                if value <= limit:
                                    try:
                                        row_dict[key] = (float(value), color) # general case must be float not int
                                    except:
                                        row_dict[key] = (str(value), color)
                                    break
                            break
                if not key in row_dict:
                    try:
                        row_dict[key] = float(value)
                    except:
                        row_dict[key] = str(value)

        data[int(row[order_by])] = row_dict
    
    return data

def get_names_for_all_column_headers():
    sites = Site.objects.all()
    deployments = Deployment.objects.all()

    return_dict = {}
    deployments_info = LastUpdatedOrderedDict()
    site_names = LastUpdatedOrderedDict()
    deployment_ids = []
    
    for site in sites:
        if not int(site.ID) in site_names:
            site_names[int(site.ID)] = ''
        site_names[int(site.ID)] = str(site.name).capitalize()
        site_names[int(site.ID)] = site_names[int(site.ID)][:4] + " " + site_names[int(site.ID)][4:]
    
    for deployment in deployments:
        deployment_ids.append(int(deployment.ID))
        if not int(deployment.ID) in deployments_info:
            deployments_info[int(deployment.ID)] = LastUpdatedOrderedDict()

        #deployments_info[int(deployment.ID)]['name'] = str(deployment.name)
        deployments_info[int(deployment.ID)]['description'] = truncate(str(deployment.description), 30)
        deployments_info[int(deployment.ID)]['project'] = truncate(str(deployment.projectID), 30)
        deployments_info[int(deployment.ID)]['target'] = str(deployment.targetID)
        deployments_info[int(deployment.ID)]['tx'] = str(deployment.txID)
        deployments_info[int(deployment.ID)]['is_active'] = 'YES' if int(deployment.is_active) else 'NO'
    
    return_dict['site_names'] = site_names
    return_dict['deployments_info'] = deployments_info
    return_dict['deployment_ids'] = deployment_ids
    return_dict['table_variables'] = get_variables_for_all_tables()
    return_dict['colors'] = init_color_values()
    return return_dict

def truncate(text, size):
    if len(text) > size:
        text = text[:size] + '...'
    return text

def get_variables_for_all_tables():
    table_variables = {}
    table_variables['telemetry'] = ['intemp', 'extemp', 'voltage', 'avg_ping_power', 'avg_ping_computer', 'last_ping_power', 'last_ping_computer', 'site_status']
    table_variables['detcount'] = ['server', 'site']
    table_variables['estcount'] = ['server']
    table_variables['timecheck'] = ['time_offset']
    table_variables['est'] = ['num_of_records', 'num_false_positives', 'num_true_positives', 'num_of_misses', 'srn', 'perceived_pulse_rate']
    table_variables['bearing'] = ['num_of_bearings', 'curr_bearing_per_site', 'likelihood_per_site', 'activity_per_site']
    table_variables['position'] = ['num_of_positions', 'curr_position', 'activity_level', 'likelihood']
    table_variables['track_pos'] = ['num_of_track_positions']
    table_variables['processing_statistics'] = ['number_records_input', 'number_records_output', 'output_processing_rate']
    table_variables['processing_cursor'] = ['value', 'record_not_processed']

    return table_variables

def init_color_values():
# current bearing per deployment per site -
#   some gradiant from 0-360, would be nice if it wrapped around so 0 and 360 were the same color but 90 and 270 were different
# current position per deployment -
#   some gradient representing distance from the center of the reserve (in location table), possibly closer to center being green and furthest out being red
    
    file_path = 'graph/colors.dat'
    colors = []
    return_dict = {}
    f = open(file_path)

    for line in f.readlines():
        if line[0] == '#':
            colors.append(line.strip())
        elif line[0] == '$':
            variable_limits = line.split(',')
            variable_limits[0] = variable_limits[0][1:]
            return_dict[variable_limits[0]] = {}

            for tup in variable_limits[1:]:
                limit = tup.split(':')
                if limit[0] == 'MAX':
                    limit[0] = sys.maxint
                return_dict[variable_limits[0]][float(limit[0])] = colors[int(limit[1])]
            return_dict[variable_limits[0]] = OrderedDict(sorted(return_dict[variable_limits[0]].items(), key=lambda t: t[0]))
    
    return return_dict