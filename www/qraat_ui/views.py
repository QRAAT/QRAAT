# File: qraat_ui/views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Q, Max, Min

# uncomment next line for for attachment download
# from django.core.servers.basehttp import FileWrapper

import qraat, time, datetime, json, utm, math
from pytz import utc, timezone

from qraatview.models import Position, Track, Deployment, Site, Project
from qraat_ui.forms import Form
from decimal import Decimal




def get_context(request, deps=[], req_deps=[]):
  

                # STORE ALL THE GET DATA FROM HTML FORM

  # Index for clicked point in flot
  if ('flot_index' in request.GET) and (request.GET['flot_index'] != ""):
    flot_index = int(request.GET['flot_index'])
  else:
    flot_index = None
  
  #lat and lon of clicked point in google maps
  if ('lat_clicked' in request.GET) and (request.GET['lat_clicked'] != ""):
    lat_clicked = request.GET['lat_clicked']
  else:
    lat_clicked = None
  if ('lng_clicked' in request.GET) and (request.GET['lng_clicked'] != ""):
    lng_clicked = request.GET['lng_clicked']
  else:
    lng_clicked = None

  #entered preferences from form
  if 'sites' in request.GET:
    site_checked = 1
  else:
    site_checked = None #or 0
  if 'zoom' in request.GET:
    zoom_selected = int(request.GET['zoom'])
  else:
    zoom_selected = 14
 
  
  if 'data_type' in request.GET:
    data_type = request.GET['data_type']
  else:
    data_type = None
  if 'dt_fr' in request.GET: #fix for if empty box
    datetime_from = request.GET['dt_fr']
  else:
    datetime_from = None
    datetime_from_sec = None
  if 'dt_to' in request.GET:
    datetime_to = request.GET['dt_to']
  else: 
    datetime_to = None
    datetime_to_sec = None
  if 'lk_l' in request.GET:
    lk_l = request.GET['lk_l']
  else:
    lk_l = 500.0
  if 'lk_h' in request.GET:
    lk_h = request.GET['lk_h']
  else:
    lk_h = None
  if 'act_l' in request.GET:
    act_l = request.GET['act_l']
  else:
    act_l = None
  if 'act_h' in request.GET:
    act_h = request.GET['act_h']
  else:
    act_h = None
  if 'lat_input' in request.GET:
    lat_in = request.GET['lat_input']
  else: 
    lat_in = None
  if ('graph_data' in request.GET) and (request.GET['graph_data']!= ""):
    graph_data = int(request.GET['graph_data'])
  else:
    graph_data = None
  if ('display_type' in request.GET) and (request.GET['display_type']!=""):
    display_type = int(request.GET['display_type'])
  else:
    display_type = None
 

  #print 'deps', deps[0].ID
  #print 'req_deps', req_deps[0].ID
  

  index_form = Form(deps=deps, data=request.GET or None)

  # Declare empty lists and variables
  view_type = ""
  pos_filtered_list = []
  pos_filtered_list1 = []
  selected_data = []
  selected_message = "[ Nothing clicked, or no points detected nearby ]"
  selected_index = None
  selected_index_large = None


  ''' If at least one deployment is selected from the deployment url, 
    automatically show data filtered for min/max range in the database
    for date, likelihood, and activity. '''
  
  print "lendeps", len(deps)
#  if deps[0].ID != None:
#    print "deps0", deps[0].ID
#  if deps[1].ID != None:
#    print "deps1", deps[1].ID
#  if req_deps[0].ID != None:
#    print "reqo", req_deps[0].ID

  if len(deps) != 1:
    view_type = "public"
  else:
    view_type = "deployment"

  if len(req_deps) > 0:
    
    
    dep_query = Position.objects.filter(deploymentID = req_deps[0].ID) 
    ''' Query db for min/max value for selected deployment.
        Used to automatically populate html form intial values. '''
    datetime_end =    float( dep_query.aggregate(Max('timestamp'))['timestamp__max'] )
    datetime_end_str = time.strftime('%Y-%m-%d %H:%M:%S',
              time.localtime(float(datetime_end-7*60*60)))

    #datetime_start =  float( dep_query.aggregate(Min('timestamp'))
    #                        ['timestamp__min'] )
    
    #last day that there's data for
    datetime_start = float(datetime_end - 86400.00)
    datetime_start_str = time.strftime('%Y-%m-%d %H:%M:%S',
              time.localtime(float(datetime_start-7*60*60)))
    likelihood_low =  str ((dep_query.aggregate(Min('likelihood'))
                            ['likelihood__min']) )
    likelihood_high = str( (dep_query.aggregate(Max('likelihood'))
                            ['likelihood__max']) )
    activity_low =    str( (dep_query.aggregate(Min('activity'))
                            ['activity__min']) )
    activity_high =   str( (dep_query.aggregate(Max('activity'))
                            ['activity__max']) )
    print datetime_start, datetime_end, likelihood_low, likelihood_high, activity_low, activity_high

  
    index_form.fields['dt_fr'].initial = datetime_start_str
    index_form.fields['dt_to'].initial = datetime_end_str
    index_form.fields['lk_l'].initial = likelihood_low
    index_form.fields['lk_h'].initial = likelihood_high
    index_form.fields['act_l'].initial = activity_low
    index_form.fields['act_h'].initial = activity_high
 

    ''' If there is no GET data '''
    ''' Should be changed so that default is the min/max, for values that
      are not entered in the form. The user should notified too. '''

    if datetime_from == None:
      pos_query = Position.objects.filter(
                          deploymentID = req_deps[0].ID,
                          timestamp__gte = datetime_start,
                          timestamp__lte = datetime_end,
                          likelihood__gte = likelihood_low,
                          likelihood__lte = likelihood_high,
                          activity__gte = activity_low,
                          activity__lte = activity_high
                          )

      for q in pos_query:
          # Calculate lat, lons each point
        (lat, lon) = utm.to_latlon(
                  float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
          
          # Convert timestamps to datetime strings and subtract 7 hrs
          # Not sure if localtime is the correct way to do this... FIXME
        date_string = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60)))

      # Store django objects as a python list of tuples
        pos_filtered_list.append(
            (
            q.ID,                 #0 
            q.deploymentID,       #1
            float(q.timestamp),   #2
            float(q.easting),     #3
            float(q.northing),    #4
            q.utm_zone_number,    #5
            float(q.likelihood),  #6
            float(q.activity),    #7
            (lat, lon),           #8
            q.utm_zone_letter,    #9
            date_string           #10
            ))
    else: 
          #if datetime_from and datetime_to and deps != []:
      try:
        datetime_from_sec = float( time.mktime (datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple()) )
        datetime_to_sec = float(time.mktime(datetime.datetime.strptime(datetime_to, '%Y-%m-%d %H:%M:%S').timetuple()))
        #temporary fix that doesn't take into account daylight savings
        datetime_from_sec_davis = datetime_from_sec + 7*60*60 #7 hr difference
        datetime_to_sec_davis = datetime_to_sec + 7*60*60
      #datetime_test = float(time.mktime(timezone('US/Pacific').(datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple())))
        float(act_h)
        float(act_l)
        float(lk_l)
        float(lk_h)
      except:
        datetime_from_sec = None
        datetime_to_sec = None
        datetime_from_sec_davis = None
        datetime_to_sec_davis = None
        act_h = None
        act_l = None
        lk_l = None
        lk_h = None

      
      pos_query = Position.objects.filter(
                          deploymentID = req_deps[0].ID,
                          timestamp__gte = datetime_from_sec_davis,
                          timestamp__lte = datetime_to_sec_davis,
                          likelihood__gte = lk_l,
                          likelihood__lte = lk_h,
                          activity__gte = act_l,
                          activity__lte = act_h
                          )

      for q in pos_query:
          # Calculate lat, lons each point
        (lat, lon) = utm.to_latlon(
                  float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
          
          # Convert timestamps to datetime strings and subtract 7 hrs
          # Not sure if localtime is the correct way to do this...
        date_string = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60)))

      # Store django objects as a python list of tuples
        pos_filtered_list.append(
            (
            q.ID,                 #0 
            q.deploymentID,       #1
            float(q.timestamp),   #2
            float(q.easting),     #3
            float(q.northing),    #4
            q.utm_zone_number,    #5
            float(q.likelihood),  #6
            float(q.activity),    #7
            (lat, lon),           #8
            q.utm_zone_letter,    #9
            date_string           #10
            ))
 


  # Convert time strings to Davis-timezone timestamps in seconds
  else:  #when a dep is not given (i.e public)
                  # QUERY DB FROM HTML SETTINGS
    
    try:
      datetime_from_sec = float( time.mktime (datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple()) )
      datetime_to_sec = float(time.mktime(datetime.datetime.strptime(datetime_to, '%Y-%m-%d %H:%M:%S').timetuple()))
        #temporary fix that doesn't take into account daylight savings
      datetime_from_sec_davis = datetime_from_sec + 7*60*60 #7 hr difference # FIXME
      datetime_to_sec_davis = datetime_to_sec + 7*60*60
      #datetime_test = float(time.mktime(timezone('US/Pacific').(datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple())))
      float(act_h)
      float(act_l)
      float(lk_l)
      float(lk_h)
    except:
      datetime_from_sec = None
      datetime_to_sec = None
      datetime_from_sec_davis = None
      datetime_to_sec_davis = None
      act_h = None
      act_l = None
      lk_l = None
      lk_h = None


    
    
    db_sel = Position   #can change database

    #dep_filter = ""
    #for d in dep_ids:
    #  dep_filter += "Q(deploymentID = %d), "
    #print dep_filter
  

  





  # 2nd deployment
  if len(req_deps) > 1:
    
    dep_query = Position.objects.filter(deploymentID = req_deps[1].ID) 
    ''' Query db for min/max value for selected deployment.
        Used to automatically populate html form intial values. '''
    datetime_end =    float( dep_query.aggregate(Max('timestamp'))
                            ['timestamp__max'] )
    datetime_end_str = time.strftime('%Y-%m-%d %H:%M:%S',
              time.localtime(float(datetime_end-7*60*60)))

    #datetime_start =  float( dep_query.aggregate(Min('timestamp'))
    #                        ['timestamp__min'] )
    
    #last day that there's data for
    datetime_start = float(datetime_end - 86400.00)
    datetime_start_str = time.strftime('%Y-%m-%d %H:%M:%S',
              time.localtime(float(datetime_start-7*60*60)))
    likelihood_low =  str ((dep_query.aggregate(Min('likelihood'))
                            ['likelihood__min']) )
    likelihood_high = str( (dep_query.aggregate(Max('likelihood'))
                            ['likelihood__max']) )
    activity_low =    str( (dep_query.aggregate(Min('activity'))
                            ['activity__min']) )
    activity_high =   str( (dep_query.aggregate(Max('activity'))
                            ['activity__max']) )
    print datetime_start, datetime_end, likelihood_low, likelihood_high, activity_low, activity_high

  
    index_form.fields['dt_fr'].initial = datetime_start_str
    index_form.fields['dt_to'].initial = datetime_end_str
    index_form.fields['lk_l'].initial = likelihood_low
    index_form.fields['lk_h'].initial = likelihood_high
    index_form.fields['act_l'].initial = activity_low
    index_form.fields['act_h'].initial = activity_high
 

    ''' If there is no GET data '''
    ''' Should be changed so that default is the min/max, for values that
      are not entered in the form. The user should notified too. '''

    if datetime_from == None:
      pos_query = Position.objects.filter(
                          deploymentID = req_deps[1].ID,
                          timestamp__gte = datetime_start,
                          timestamp__lte = datetime_end,
                          likelihood__gte = likelihood_low,
                          likelihood__lte = likelihood_high,
                          activity__gte = activity_low,
                          activity__lte = activity_high
                          )

      for q in pos_query:
          # Calculate lat, lons each point
        (lat, lon) = utm.to_latlon(
                  float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
          
          # Convert timestamps to datetime strings and subtract 7 hrs
          # Not sure if localtime is the correct way to do this...
        date_string = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60)))

      # Store django objects as a python list of tuples
        pos_filtered_list1.append(
            (
            q.ID,                 #0 
            q.deploymentID,       #1
            float(q.timestamp),   #2
            float(q.easting),     #3
            float(q.northing),    #4
            q.utm_zone_number,    #5
            float(q.likelihood),  #6
            float(q.activity),    #7
            (lat, lon),           #8
            q.utm_zone_letter,    #9
            date_string           #10
            ))
    else: 
          #if datetime_from and datetime_to and deps != []:
      try:
        datetime_from_sec = float( time.mktime (datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple()) )
        datetime_to_sec = float(time.mktime(datetime.datetime.strptime(datetime_to, '%Y-%m-%d %H:%M:%S').timetuple()))
        #temporary fix that doesn't take into account daylight savings
        datetime_from_sec_davis = datetime_from_sec + 7*60*60 #7 hr difference
        datetime_to_sec_davis = datetime_to_sec + 7*60*60
      #datetime_test = float(time.mktime(timezone('US/Pacific').(datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple())))
        float(act_h)
        float(act_l)
        float(lk_l)
        float(lk_h)
      except:
        datetime_from_sec = None
        datetime_to_sec = None
        datetime_from_sec_davis = None
        datetime_to_sec_davis = None
        act_h = None
        act_l = None
        lk_l = None
        lk_h = None

      
      pos_query1 = Position.objects.filter(
                          deploymentID = req_deps[1].ID,
                          timestamp__gte = datetime_from_sec_davis,
                          timestamp__lte = datetime_to_sec_davis,
                          likelihood__gte = lk_l,
                          likelihood__lte = lk_h,
                          activity__gte = act_l,
                          activity__lte = act_h
                          )

      for q in pos_query1:
          # Calculate lat, lons each point
        (lat, lon) = utm.to_latlon(
                  float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
          
          # Convert timestamps to datetime strings and subtract 7 hrs
          # Not sure if localtime is the correct way to do this...
        date_string = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60)))

      # Store django objects as a python list of tuples
        pos_filtered_list1.append(
            (
            q.ID,                 #0 
            q.deploymentID,       #1
            float(q.timestamp),   #2
            float(q.easting),     #3
            float(q.northing),    #4
            q.utm_zone_number,    #5
            float(q.likelihood),  #6
            float(q.activity),    #7
            (lat, lon),           #8
            q.utm_zone_letter,    #9
            date_string           #10
            ))
 




















  '''
    if (datetime_from_sec_davis) and (datetime_to_sec_davis) and (lk_l) and (lk_h) and (act_l) and (act_h):
      
      
    
      if (len(req_deps) >= 1):
        pos_query = Position.objects.filter(
                          deploymentID = req_deps[0].ID,
                          timestamp__gte = datetime_from_sec_davis,
                          timestamp__lte = datetime_to_sec_davis,
                          likelihood__gte = lk_l,
                          likelihood__lte = lk_h,
                          activity__gte = act_l,
                          activity__lte = act_h
                          )

        for q in pos_query:
          # Calculate lat, lons each point
          (lat, lon) = utm.to_latlon(
                  float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
          
          # Convert timestamps to datetime strings and subtract 7 hrs
          # Not sure if localtime is the correct way to do this...
          date_string = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60)))

      # Store django objects as a python list of tuples
          pos_filtered_list.append(
            (
            q.ID,                 #0 
            q.deploymentID,       #1
            float(q.timestamp),   #2
            float(q.easting),     #3
            float(q.northing),    #4
            q.utm_zone_number,    #5
            float(q.likelihood),  #6
            float(q.activity),    #7
            (lat, lon),           #8
            q.utm_zone_letter,    #9
            date_string           #10
            ))
        


      if (len(req_deps) >= 2):
        pos_query1 = Position.objects.filter(
                            deploymentID = req_deps[1].ID,
                            timestamp__gte = datetime_from_sec_davis,
                            timestamp__lte = datetime_to_sec_davis,
                            likelihood__gte = lk_l,
                            likelihood__lte = lk_h,
                            activity__gte = act_l,
                            activity__lte = act_h
                            )

        for q in pos_query1:
          # Calculate lat, lons each point
          (lat, lon) = utm.to_latlon(
                  float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
            
          date_string = time.strftime(
            '%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60))
          )

   
        # Store django objects as a python list of tuples
          pos_filtered_list1.append(
            (
            q.ID,                 #0
            q.deploymentID,       #1
            float(q.timestamp),   #2
            float(q.easting),     #3
            float(q.northing),    #4
            q.utm_zone_number,    #5
            float(q.likelihood),  #6
            float(q.activity),    #7
            (lat, lon),           #8
            q.utm_zone_letter,    #9
            date_string           #10
            ))



      if (len(req_deps) >= 3):
        pos_query2 = db_sel.objects.filter(
                            deploymentID = req_deps[2].ID,
                            timestamp__gte = datetime_from_sec_davis,
                            timestamp__lte = datetime_to_sec_davis,
                            likelihood__gte = lk_l,
                            likelihood__lte = lk_h,
                            activity__gte = act_l,
                            activity__lte = act_h
                            )

      if (len(req_deps) >= 4):
        pos_query3 = db_sel.objects.filter(
                            deploymentID = req_deps[3].ID,
                            timestamp__gte = datetime_from_sec_davis,
                            timestamp__lte = datetime_to_sec_davis,
                            likelihood__gte = lk_l,
                            likelihood__lte = lk_h,
                            activity__gte = act_l,
                            activity__lte = act_h
                            ) 
  '''

            #OLD WAY TO QUERY, either with only one deployment, 
            #or trying to make multiple querysets without repeating code

#pos_query = db_sel.objects.filter(
    #                      # Q is used for or. These need to be in beginning
    #                      
    #                      #Q(deploymentID = 63) | Q(deploymentID = 64),
    #                      deploymentID = 63,
    #                      timestamp__gte = datetime_from_sec_davis,
    #                      timestamp__lte = datetime_to_sec_davis,
    #                      likelihood__gte = lk_l,
    #                      likelihood__lte = lk_h,
    #                      activity__gte = act_l,
    #                      activity__lte = act_h
    #                      )


  # Note: To pass strings to js using json, use |safe in template.



  # Site list
  sites = []
  for s in Site.objects.all():
    sites.append((
      s.ID,                   # [0] 
      s.name,                 # [1]
      s.location,             # [2]
      float(s.latitude),      # [3]
      float(s.longitude),     # [4]
      float(s.easting),       # [5]
      float(s.northing),      # [6]
      s.utm_zone_number,      # [7]
      s.utm_zone_letter,      # [8]
      float(s.elevation)))    # [9]




                # FIND NEAREST POINT WHEN MAP IS CLICKED


  # Get clicked lat, lon from js event --> html form
  # Convert them to utm
  if pos_filtered_list and lat_clicked and lng_clicked:  
        
    (easting_clicked, northing_clicked, utm_zone_number_clicked, utm_zone_letter_clicked) = utm.from_latlon(float(lat_clicked), float(lng_clicked))

  # Truncate northing and easting for the query
  # Divide by 10 (click needs to be closer) or 100 (less accurate) to increase the distance allowed between the clicked point and the actual point
    northing_clicked_trunc = (int(northing_clicked))/1000
    easting_clicked_trunc = (int(easting_clicked))/1000

  # Query the data that matches the northing and easting 
    filtered_list = pos_query.filter(
      northing__startswith=northing_clicked_trunc, 
      easting__startswith=easting_clicked_trunc).order_by('-northing', '-easting')
    selected_list = []
    for f in filtered_list:
      selected_list.append(
        math.sqrt(
        (northing_clicked - float(f.northing)) *
          (northing_clicked - float(f.northing))
        + (easting_clicked - float(f.easting)) * 
          (easting_clicked - float(f.easting))
        )
      )
  
  # Get the index of the smallest distance
    if filtered_list:
      selected_message = ""
      selected_index = selected_list.index(min(selected_list))
  
  # Get the data corresponding to the selected index
      sel = filtered_list[selected_index]

      (lat_clicked_point, lng_clicked_point) = utm.to_latlon(
                                          float(sel.easting), 
                                          float(sel.northing),
                                          sel.utm_zone_number,
                                          sel.utm_zone_letter
                                          )
      selected_data.append(
      (
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
          (
          float(lat_clicked_point),    # [10][0]: lat of db data closest to click
          float(lng_clicked_point)     # [10][1]: lng of db data closest to click
          ),
        time.strftime('%Y-%m-%d %H:%M:%S', # [11]: date string in Davis time
          time.localtime(float(sel.timestamp-7*60*60))),
        sel.utm_zone_letter     # utm zone letter
      ))
    

  #get the index in the original filtered list, for the clicked pt
      pos_filtered_list_IDs = [int(x[0]) for x in pos_filtered_list]
      selected_index_large = pos_filtered_list_IDs.index(long(selected_data[0][2]))






                  # IF FLOT IS SELECTED:
          # Populate selected_data list with data based on index
          # This could probably be changed to work with flight_latlon_pos

  elif flot_index:
    selected_data.append((
        None,   # [0]: nothing clicked
        None,   # [1]: nothing clicked
        pos_filtered_list[flot_index][0],   # [2]: ID
        pos_filtered_list[flot_index][1],   # [3]: deploymentID
        float(pos_filtered_list[flot_index][2]), # [4]: timestamp
        float(pos_filtered_list[flot_index][3]), # [5]: easting
        float(pos_filtered_list[flot_index][4]), # [6]: northing
        pos_filtered_list[flot_index][5], # [7]: utm zone number
        float(pos_filtered_list[flot_index][6]), # [8]: likelihood
        float(pos_filtered_list[flot_index][7]), # [9]: activity
        
        # [10]: tuple: [10][0]: lat, [10][1]: lon
        (
          float(pos_filtered_list[flot_index][8][0]),
          float(pos_filtered_list[flot_index][8][1])
        ), #lon
        
        # [11] Davis time string converted from timestamp UTC seconds
        time.strftime(
          '%Y-%m-%d %H:%M:%S', 
          time.localtime(
            float(pos_filtered_list[flot_index][2]-7*60*60)
          )
        ),
        
        # [12] utm zone letter
        pos_filtered_list[flot_index][9]
      ))




  #the following lines sets the default as '63' for deploymentID
  #index_form.fields['trans'].initial = ['63']

  context = {
            #public, deployment, project, etc.
            'view_type': json.dumps(view_type),

            #plot & related data
            'pos_data': json.dumps(pos_filtered_list),             
            
            #for getting the no. of positions
            'positions': pos_filtered_list,

            #2nd deployment js array
            'pos_data1': json.dumps(pos_filtered_list1),

            #2nd deployment django array
            'positions1': pos_filtered_list1,
            
            #for plotting the site markers
            'siteslist': json.dumps(sites), 
            
            #for displaying html form
            #'form': Form(deps=deps, data=request.GET or None), 
            'form': index_form,
            #selected transmitter from form
            #'tx': json.dumps(tx), 
            
            #if sites should be shown
            'site_checked': json.dumps(site_checked), 
            
            #clicked point's data, note: string
            'selected_data': json.dumps(selected_data), 
            
            #actvty vs lklhood graphed
            'graph_data': json.dumps(graph_data), 
            
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
            
            #'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
            #'zoom': json.dumps(zoom_selected), 
              #not used anymore
            #'data_type': json.dumps(data_type), 
              #position vs track (not used?)
        
            }
  
  return context





# another view, for exporting/downloading kml file attachment
#def export(request):
#  response = HttpResponse(content_type='text/csv')
#  reponse['Content-Dispotision'] = 'attachment: filename="qraat_data.csv"'
#
#  writer = csv.writer(response)
#  for row in positions: 
#    writer.writerow(['lat', 'lon'])
#
#  return response
    #?? download kml file attachment
    #return render(request, 'index.html', context)
    #response = HttpResponse(mimetype='text/plain')
    #response['Content-Disposition'] = 'attachement; filename="%s.txt"' %p.uuid
    #response.write(p.body)


def index(request):
  ''' Compile a list of public deployments, make this available. 
      Don't initially display anything. ''' 

  #''' SELECT * FROM deployment JOIN project 
  #      ON deployment.projectID = project.ID 
  #   WHERE project.is_public = True ''' 
  # TODO filter deps by form data. 
  if request.GET.getlist('trans') != None:
    req_deps = Deployment.objects.filter(ID__in=request.GET.getlist('trans'))
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



