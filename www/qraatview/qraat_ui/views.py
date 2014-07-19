# File: qraat_ui/views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
# uncomment next line for for attachment download
# from django.core.servers.basehttp import FileWrapper
import qraat, time, datetime, json, utm, math

from qraat_ui.models import Position, track, Deployment, Site
from qraat_ui.forms import Form
from decimal import Decimal

def index(request):
  #to pass strings to js, use |safe in template.
  #site list
  sites = []
  for s in Site.objects.all():
    sites.append((s.ID, s.name, float(s.latitude), float(s.longitude), float(s.easting), float(s.northing), s.utm_zone_number, s.utm_zone_letter, float(s.elevation)))
  
  #transmitter list
  tx_IDs = []
  for d in Deployment.objects.all():
    if (d.time_end != None):
      tx_IDs.append((d.ID, float(d.time_start), float(d.time_end), 
      d.txID, d.targetID, d.projectID, d.is_active, d.is_hidden))
    elif (d.time_end == None):
      tx_IDs.append((d.ID, float(d.time_start), d.time_end, d.txID,
      d.targetID, d.projectID, d.is_active, d.is_hidden))
  
  #index for clicked point in flot
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
  if 'trans' in request.GET:
    tx = request.GET['trans']
  else:
    tx = None
  if 'data_type' in request.GET:
    data_type = request.GET['data_type']
  else:
    data_type = None
  if 'dt_fr' in request.GET: #fix for if empty box
    dt_fr = request.GET['dt_fr']
  else:
    dt_fr = None
    dt_fr_sec = None
  if 'dt_to' in request.GET:
    dt_to = request.GET['dt_to']
  else: 
    dt_to = None
    dt_to_sec = None
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
  if 'graph_data' in request.GET:
    graph_data = int(request.GET['graph_data'])
  else:
    graph_data = None
  if 'display_type' in request.GET:
    display_type = int(request.GET['display_type'])
  else:
    display_type = None
  
  #old
  if 'lng_input' in request.GET:
    lng_in = request.GET['lng_input']
  else:
    lng_in = None
  
  pos_filtered_list = []
  selected_data = []
  selected_message = "[ Nothing clicked, or no points detected nearby ]"
  selected_index = None
  selected_index_large = None
  dt_str = None

  #if form.is_valid():
  if dt_fr and dt_to:
    dt_fr_sec = float(time.mktime(datetime.datetime.strptime(dt_fr, '%Y-%m-%d %H:%M:%S').timetuple()))
    dt_to_sec = float(time.mktime(datetime.datetime.strptime(dt_to, '%Y-%m-%d %H:%M:%S').timetuple()))
    
    db_sel = Position   #can change database
    pos_query = db_sel.objects.filter(
                          timestamp__gte = dt_fr_sec,
                          timestamp__lte = dt_to_sec,
                          deploymentID = tx,
                          likelihood__gte = lk_l,
                          likelihood__lte = lk_h,
                          activity__gte = act_l,
                          activity__lte = act_h
                          )
    for q in pos_query:

      (lat, lon) = utm.to_latlon(float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
      pos_filtered_list.append((q.ID, q.deploymentID, float(q.timestamp), 
                      float(q.easting), float(q.northing),
                      q.utm_zone_number,
                      float(q.likelihood), float(q.activity),
                      (lat, lon), q.utm_zone_letter))

#get clicked lat, lon from js event --> html form
#convert them to utm
  if lat_clicked and lng_clicked:  
    selected_data.append(float(lat_clicked))
    selected_data.append(float(lng_clicked))
    (easting_c, northing_c, utm_zone_number_c, utm_zone_letter_c) = utm.from_latlon(float(lat_clicked), float(lng_clicked))

#truncate northing and easting for the query
#divide by 10 (click needs to be closer) or 100 (less accurate) to increase the distance allowed between the clicked point and the actual point
    northing_c_trunc = (int(northing_c))/1000
    easting_c_trunc = (int(easting_c))/1000
# query the data that matches the northing and easting 
    filtered_list = pos_query.filter(
      northing__startswith=northing_c_trunc, 
      easting__startswith=easting_c_trunc).order_by('-northing', '-easting')
    selected_list = []
    for f in filtered_list:
      selected_list.append(
        math.sqrt(
        (northing_c - float(f.northing)) * (northing_c - float(f.northing))
        + (easting_c - float(f.easting)) * (easting_c - float(f.easting))
        ))
#get the index of the smallest distance
    if filtered_list:
      selected_message = ""
      selected_index = selected_list.index(min(selected_list))
#get the data corresponding to the selected index
      sel = filtered_list[selected_index]
      selected_data.append(sel.ID)
      selected_data.append(sel.deploymentID)
       # time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(sel.timestamp)))
      # if (selected_data = filtered_list)

      selected_data.append(float(sel.timestamp))
      selected_data.append(float(sel.easting)) 
      selected_data.append(float(sel.northing)) 
      selected_data.append(sel.utm_zone_number) 
      selected_data.append(float(sel.likelihood)) 
      selected_data.append(float(sel.activity))

      (lat_c, lon_c) = utm.to_latlon(float(sel.easting), 
                  float(sel.northing),
                  sel.utm_zone_number,
                  sel.utm_zone_letter)
      selected_data.append((lat_c, lon_c))
      selected_data.append( time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(sel.timestamp))) )
      selected_data.append(sel.utm_zone_letter)
    #get the index in the original filtered list, for the clicked pt
      pos_filtered_list_IDs = [int(x[0]) for x in pos_filtered_list]
      selected_index_large = pos_filtered_list_IDs.index(long(selected_data[2]))

#the date & time string. didn't work when in the sel list

  elif flot_index:
    selected_data.append(None) #no clicked lat
    selected_data.append(None) #no clicked lng
    selected_data.append(pos_filtered_list[flot_index][0]) #position ID
    selected_data.append(pos_filtered_list[flot_index][1]) #deployment ID
    selected_data.append(float(pos_filtered_list[flot_index][2])) #timestamp
    selected_data.append(float(pos_filtered_list[flot_index][3])) #easting
    selected_data.append(float(pos_filtered_list[flot_index][4])) #northing
    selected_data.append(pos_filtered_list[flot_index][5]) #utm zone number
    selected_data.append(float(pos_filtered_list[flot_index][6])) #likelihood
    selected_data.append(float(pos_filtered_list[flot_index][7])) #activity
    selected_data.append((float(pos_filtered_list[flot_index][8][0]) , float(pos_filtered_list[flot_index][8][1]))) #lon
    selected_data.append( time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(pos_filtered_list[flot_index][2]))) )
    selected_data.append(pos_filtered_list[flot_index][9])
    
    print selected_data
    
  print pos_filtered_list

  context = {
            'pos_data': json.dumps(pos_filtered_list), #plot & related data
            'positions': pos_filtered_list, #for getting the no. of positions
            'siteslist': json.dumps(sites), #for plotting the site markers
            'form': Form(request.GET or None), #for displaying html form
            'tx': json.dumps(tx), #selected transmitter from form
            'site_checked': json.dumps(site_checked), #if sites should be shown
            'selected_data': json.dumps(selected_data), #clicked point's data, note: string
            'graph_data': json.dumps(graph_data), #actvty vs lklhood graphed
            'selected_message': selected_message, #if pos successfully clicked
            'selected_index': selected_index, #map-clicked i in filtered pos_data
            'selected_index_large': selected_index_large, #clicked i in pos_data
            'flot_index': json.dumps(flot_index), #flot selected i in pos_data
            'display_type': json.dumps(display_type),
            #'dt_fr': dt_fr_sec, #not used
            #'dt_to': dt_to_sec, #not used
            #'tx_IDs': tx_IDs, #Don't think this is actually be used anywhere
            #'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
            #'zoom': json.dumps(zoom_selected), #not used anymore
            #'data_type': json.dumps(data_type), #position vs track (not used?)
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
