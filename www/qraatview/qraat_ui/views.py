# File: qraat_ui/views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
# uncomment next line for for attachment download
# from django.core.servers.basehttp import FileWrapper
import qraat, time, datetime, json, utm, math

from qraat_ui.models import Position, tx_ID, track, sitelist
from qraat_ui.forms import Form
from decimal import Decimal

def index(request):
  #json has trouble processing strings???
  sites = []
  for s in sitelist.objects.all():
    sites.append((s.ID, float(s.latitude), float(s.longitude)))
    #sites.append((s.ID, s.name, s.location, float(s.latitude),
    #              float(s.longitude), float(s.easting), 
    #              float(s.northing), s.utm_zone_number, s.rx))
  
  if ('lat_clicked' in request.GET) and (request.GET['lat_clicked'] != ""):
    lat_clicked = request.GET['lat_clicked']
  else:
    lat_clicked = None
  if ('lng_clicked' in request.GET) and (request.GET['lng_clicked'] != ""):
    lng_clicked = request.GET['lng_clicked']
  else:
    lng_clicked = None
  
  if 'sites' in request.GET:
    site_checked = 1
  else:
    site_checked = None #or 0
  if 'lk' in request.GET:
    lk_checked = 1
  else:
    lk_checked = None
  if 'activity' in request.GET:
    act_checked = 1
  else:
    act_checked = None
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
  if 'lat_input' in request.GET:
    lat_in = request.GET['lat_input']
  else: 
    lat_in = None
  
  if 'lng_input' in request.GET:
    lng_in = request.GET['lng_input']
  else:
    lng_in = None
  if 'graph_data' in request.GET:
    graph_data = int(request.GET['graph_data'])
  else:
    graph_data = None

  pos_filtered_list = []
  selected_data = []
  selected_message = "[ Nothing clicked, or no points detected nearby ]"
  selected_index = None
  dt_str = None

  #if form.is_valid():
  if dt_fr and dt_to:
    dt_fr_sec = float(time.mktime(datetime.datetime.strptime(dt_fr, '%Y-%m-%d %H:%M:%S').timetuple()))
    dt_to_sec = float(time.mktime(datetime.datetime.strptime(dt_to, '%Y-%m-%d %H:%M:%S').timetuple()))
    
    pos_filtered_list = []
    db_sel = Position   #can change database
    pos_query = db_sel.objects.filter(
                          timestamp__gte=dt_fr_sec,
                          timestamp__lte=dt_to_sec,
                          depID=tx,
                          likelihood__gte=lk_l,
                          likelihood__lte=lk_h)


    #pos_query = Position.objects.filter(
    #                      timestamp__gte=dt_fr_sec,
    #                      timestamp__lte=dt_to_sec,
    #                      depID=tx,
    #                      likelihood__gte=lk_l,
    #                      likelihood__lte=lk_h)
    for q in pos_query:

      (lat, lon) = utm.to_latlon(float(q.easting), 
                  float(q.northing),
                  q.utm_zone_number,
                  q.utm_zone_letter)
      pos_filtered_list.append((q.ID, q.depID, float(q.timestamp), 
                      float(q.easting), float(q.northing),
                      q.utm_zone_number, #p.utm_zone_letter,
                      float(q.likelihood), float(q.activity),
                      (lat, lon)))

#get clicked lat, lon from js event --> html form
#convert them to utm
  if lat_clicked and lng_clicked:  
    selected_data.append(float(lat_clicked))
    selected_data.append(float(lng_clicked))
    (easting_c, northing_c, utm_zone_number_c, utm_zone_letter_c) = utm.from_latlon(float(lat_clicked), float(lng_clicked))

#truncate northing and easting for the query
#divide by 10 (click needs to be closer) or 100 (less accurate) to increase the distance allowed between the clicked point and the actual point
    northing_c_trunc = (int(northing_c))/100
    easting_c_trunc = (int(easting_c))/100
# query the data that matches the northing and easting 
    filtered_list = pos_query.filter(
      northing__startswith=northing_c_trunc, 
      easting__startswith=easting_c_trunc).order_by('-northing', '-easting')
    selected_list = []
    for f in filtered_list:
      selected_list.append(
        math.sqrt(
        (4260347.98 - float(f.northing)) * (4260347.98 - float(f.northing))
        + (573186.64 - float(f.easting)) * (573186.64 - float(f.easting))
        ))
#get the index of the smallest distance
    if filtered_list:
      
      selected_message = ""

      selected_index = selected_list.index(min(selected_list))
#get the data corresponding to the selected index
      sel = filtered_list[selected_index]
      selected_data.append(sel.ID)
      selected_data.append(sel.depID)
       # time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(sel.timestamp)))
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

#the date & time string. didn't work when in the sel list
      dt_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(sel.timestamp)))


  context = {
            'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
            'pos_data': json.dumps(pos_filtered_list),
            'siteslist': json.dumps(sites),
            'form': Form(request.GET or None),
            'positions': pos_filtered_list,
            'lk_checked': json.dumps(lk_checked),
            'act_checked': json.dumps(act_checked),
            'tx': json.dumps(tx),
            'data_type': json.dumps(data_type),
            'dt_fr': dt_fr_sec,
            'dt_to': dt_to_sec,
            'site_checked': json.dumps(site_checked),
            'zoom': json.dumps(zoom_selected),
            'selected_data': json.dumps(selected_data),
            'dt_str': json.dumps(dt_str),
            'graph_data': json.dumps(graph_data),
            'selected_message': selected_message,
            'selected_index': selected_index,
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
