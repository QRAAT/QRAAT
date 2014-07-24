# File: qraat_ui/views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Q

# uncomment next line for for attachment download
# from django.core.servers.basehttp import FileWrapper

import qraat, time, datetime, json, utm, math
from pytz import utc, timezone

from qraat_ui.models import Position, track, Deployment, Site
from qraat_ui.forms import TestForm
from decimal import Decimal




def index(request, depID=None):
  

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
 



  #if 'trans' in request.GET and not depID:
  #  tx = request.GET['trans']
  dep_list = [] 
  if 'trans' in request.GET and not depID:
    dep_list = request.GET.getlist('trans')
    #dep_list_length = len(dep_list)



  else:
    tx = depID
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
 



  # Declare empty lists and variables

  pos_filtered_list = []
  pos_filtered_list1 = []
  selected_data = []
  selected_message = "[ Nothing clicked, or no points detected nearby ]"
  selected_index = None
  selected_index_large = None




  # Convert time strings to Davis-timezone timestamps in seconds


  #if form.is_valid():
  if datetime_from and datetime_to:
    try:
      datetime_from_sec = float( time.mktime (datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple()) )
      datetime_to_sec = float(time.mktime(datetime.datetime.strptime(datetime_to, '%Y-%m-%d %H:%M:%S').timetuple()))
      
      #make sure these are numbers
      float(lk_l)
      float(lk_h)
      float(act_l)
      float(act_h)
      
      #temporary fix that doesn't take into account daylight savings
      datetime_from_sec_davis = datetime_from_sec + 7*60*60 #7 hr difference
      datetime_to_sec_davis = datetime_to_sec + 7*60*60

      #datetime_test = float(time.mktime(timezone('US/Pacific').(datetime.datetime.strptime(datetime_from, '%Y-%m-%d %H:%M:%S').timetuple())))

      print datetime_from_sec
      #print datetime_test 

    except:
      datetime_from_sec = None
      datetime_to_sec = None
      datetime_from_sec_davis = None
      datetime_to_sec_davis = None


                  # QUERY DB FROM HTML SETTINGS


    db_sel = Position   #can change database

    #dep_filter = ""
    #for d in dep_list:
    #  dep_filter += "Q(deploymentID = %d), "
    #print dep_filter
    
    if (datetime_from_sec_davis) and (datetime_to_sec_davis) and (lk_l) and (lk_h) and (act_l) and (act_h):
      if (len(dep_list) >= 1):
        pos_query = db_sel.objects.filter(
                          deploymentID = dep_list[0],
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
          date_string = time.strftime(
            '%Y-%m-%d %H:%M:%S',
            time.localtime(float(q.timestamp-7*60*60))
            )

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
            



      if (len(dep_list) >= 2):
        pos_query1 = db_sel.objects.filter(
                          deploymentID = dep_list[1],
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


      #print len(pos_filtered_list)
      #print len(pos_filtered_list1)
      #print dep_list
      #print len(dep_list)


      #if (len(dep_list) >= 3):
      #  pos_query2 = db_sel.objects.filter(
      #                    deploymentID = dep_list[2],
      #                    timestamp__gte = datetime_from_sec_davis,
      #                    timestamp__lte = datetime_to_sec_davis,
      #                    likelihood__gte = lk_l,
      #                    likelihood__lte = lk_h,
      #                    activity__gte = act_l,
      #                    activity__lte = act_h
      #                    )

      #if (len(dep_list) >= 4):
      #  pos_query3 = db_sel.objects.filter(
      #                    deploymentID = dep_list[3],
      #                    timestamp__gte = datetime_from_sec_davis,
      #                    timestamp__lte = datetime_to_sec_davis,
      #                    likelihood__gte = lk_l,
      #                    likelihood__lte = lk_h,
      #                    activity__gte = act_l,
      #                    activity__lte = act_h
      #                    ) 



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

  print sites



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
        time.strftime(           # [11]: date string in Davis time
          '%Y-%m-%d %H:%M:%S', 
          time.localtime(float(sel.timestamp-7*60*60))
          ),
        sel.utm_zone_letter     # utm zone letter
      ))
    

  #get the index in the original filtered list, for the clicked pt
      pos_filtered_list_IDs = [int(x[0]) for x in pos_filtered_list]
      selected_index_large = pos_filtered_list_IDs.index(long(selected_data[0][2]))






                  # IF FLOT IS SELECTED:
          # Populate selected_data list with data based on index
          # This could probably be changed to work with flight_latlon_pos

  elif flot_index:
    print flot_index
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



  index_form = TestForm(depID=depID, data=request.GET or None)
  
  #the following lines sets the default as '63' for deploymentID
  #index_form.fields['trans'].initial = ['63']
  

  context = {

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

  return render(request, 'index.html', context)





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



def view_by_dep_id(request, depID):
  return HttpResponse('Not implemneted yet.')
