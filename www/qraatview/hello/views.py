# views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
import qraat, time, datetime, json, utm, math

from hello.models import Position, tx_ID, track, sitelist
from hello.forms import Form


def index(request):
  #json has trouble processing strings???

  sites = []
  for s in sitelist.objects.all():
    sites.append((s.ID, float(s.latitude), float(s.longitude)))
    #sites.append((s.ID, s.name, s.location, float(s.latitude),
    #              float(s.longitude), float(s.easting), 
    #              float(s.northing), s.utm_zone_number, s.rx))


#site_checked is not in the try section because json.dumps has issues with strings, and the field type is boolean, so there it won't be there for off
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
    zoom_selected = request.GET['zoom']
  else:
    zoom_selected = 14

  print zoom_selected


  try:
    tx = request.GET['trans']
    data_type = request.GET['data_type']
    dt_fr = request.GET['dt_fr']
    dt_to = request.GET['dt_to']
    # zoom = int(request.GET['zoom'])
    lk_l = request.GET['lk_l']
    lk_h = request.GET['lk_h']
    #lat_lon = request.GET['ll']
    #north_east = request.GET['ne']
    #like = request.GET['lk']
    #like_low = request.GET['lk_l']
    #like_high = request.GET['lk_h']
    lat_in = request.GET['lat_input']
    lng_in = request.GET['lng_input']

  except:
    positions = []
   # for p in Position.objects.all()[:0]:
   #   (lat, lon) = utm.to_latlon(float(p.easting), 
   #               float(p.northing),
   #               p.utm_zone_number,
   #               p.utm_zone_letter)
   #   positions.append((p.ID, p.depID, float(p.timestamp), 
   #                   float(p.easting), float(p.northing),
   #                   p.utm_zone_number, #p.utm_zone_letter,
   #                   float(p.likelihood), float(p.activity),
   #                   (lat, lon)))
    selected_data = []

    context = {
            #same
              'pos_data': json.dumps(positions),
              'positions': positions,
              'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
              'siteslist': json.dumps(sites),
              'form': Form(),
              'lk_checked': json.dumps(lk_checked),
              'act_checked': json.dumps(act_checked),
            #unique to except (if no form data was entered
              'message': "ERROR: Please select a data type, transmitter, and date range.",
              'site_checked': json.dumps(site_checked),
              'zoom': json.dumps(zoom_selected),
              'selected_data': selected_data,
              }

    return render(request, 'index.html', context)
  
  else:
    #if form.is_valid():
    dt_fr_sec = float(time.mktime(datetime.datetime.strptime(dt_fr,
                '%Y-%m-%d %H:%M:%S').timetuple()))
    dt_to_sec = float(time.mktime(datetime.datetime.strptime(dt_to,
                '%Y-%m-%d %H:%M:%S').timetuple()))
    
    pos_filtered_list = []
    #pos_query = Position.objects.filter(timestamp__gte=dt_fr_sec, timestamp__lte=dt_to_sec, depID=tx)
    pos_query = Position.objects.filter(timestamp__gte=dt_fr_sec, timestamp__lte=dt_to_sec, depID=tx, likelihood__gte=lk_l, likelihood__lte=lk_h)
 
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


# find smallest distance between database positions and user clicked lat/lon
    # (easting_c, northing_c, utm_zone_number_c, utm_zone_letter_c)  = utm.from_latlon(latitude_c, longitude_c)
    # #truncate northing_c  and easting_c:
    # northing_c_trunc = "%.3f" %northing_c
    # easting_c_trunc = "%.3f" %easting_c
    # clicked_data = pos_query.filter(northing__contains=northing_c_trunc, easting__contains=easting_c_trunc).order_by('-northing', '-easting')

    # distances = []
    # northing_clicked = northing_c  in clicked_data
    # distances.append( sqrt( (northing - northing_c)^2 + (easting = easting_clicked)^2 ) )
    
#get the clicked latitude and clicked longitude from javascript event
#convert them to utm
    
    (easting_c, northing_c, utm_zone_number_c, utm_zone_letter_c) = utm.from_latlon(float(lat_in), float(lng_in))

#    (easting_c, northing_c, utm_zone_number_c, utm_zone_letter_c) = utm.from_latlon(38.488473, -122.160824)
#truncate northing and easting for the query
    northing_c_trunc = int(northing_c)
    easting_c_trunc = int(easting_c)

    #northing_c_trunc = "%3f" %northing_c
    #easting_c_trunc = "%.3f" %easting_c
  #  print northing_c_trunc
  #  print easting_c_trunc

#query the data that matches the northing and easting 
    filtered_list = Position.objects.filter(northing__startswith=northing_c_trunc, easting__startswith=easting_c_trunc)#.order_by('-northing', '-easting')
 #   print filtered_list
    selected_list = []
    for f in filtered_list:
      selected_list.append(math.sqrt((4260347.98 - float(f.northing)) * (4260347.98 - float(f.northing)) + (573186.64 - float(f.easting)) * (573186.64 - float(f.easting))))
    
#get the index of the smallest distance
    if filtered_list:
      selected_index = selected_list.index(min(selected_list))

#    print selected_index
#get the data corresponding to the selected index
      sel = filtered_list[selected_index]
   # print selected_data.northing
   # print selected_data.easting
   # print selected_data.ID
      print sel.likelihood
      selected_data = [sel.ID, sel.depID, float(sel.timestamp), float(sel.easting), float(sel.northing), sel.utm_zone_number, float(sel.likelihood), float(sel.activity)]

    else:
      selected_data = []

    context = {
          #same
            'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
            'pos_data': json.dumps(pos_filtered_list),
            'siteslist': json.dumps(sites),
            'form': Form(request.GET or None),
            'positions': pos_filtered_list,
            'lk_checked': json.dumps(lk_checked),
            'act_checked': json.dumps(act_checked),

          #unique to else (if form data was entered)
            'tx': json.dumps(tx),
            'data_type': json.dumps(data_type),
            'dt_fr': dt_fr_sec,
            'dt_to': dt_to_sec,
            'site_checked': json.dumps(site_checked),
            'zoom': json.dumps(zoom_selected),
            'selected_data': json.dumps(selected_data),
            }

    return render(request, 'index.html', context)


#------------------- end of maps4 class----------------

def maps3(request):
  context = {}
  return render(request, 'maps3.html', context)
