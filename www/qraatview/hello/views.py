# views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
import qraat, time, datetime, json, utm

from hello.maps import Convert
from hello.models import Position, tx_ID, track, sitelist
from hello.forms import Form

def maps4(request):
  positions = []
  #for p in Position.objects.all():
  for p in Position.objects.all()[:1000]:
    (lat, lon) = utm.to_latlon(float(p.easting), 
                  float(p.northing),
                  p.utm_zone_number,
                  p.utm_zone_letter)
    positions.append((p.ID, p.depID, float(p.timestamp), 
                      float(p.easting), float(p.northing),
                      p.utm_zone_number, #p.utm_zone_letter,
                      float(p.likelihood), float(p.activity),
                      (lat, lon)))

 
  sites = []
  for s in sitelist.objects.all():
    sites.append((s.ID, float(s.latitude), float(s.longitude)))
    #sites.append((s.ID, s.name, s.location, float(s.latitude),
    #              float(s.longitude), float(s.easting), 
    #              float(s.northing), s.utm_zone_number, s.rx))


  try:
    tx = request.GET['trans']
    data_type = request.GET['data_type']
    dt_fr = request.GET['dt_fr']
    dt_to = request.GET['dt_to']
    zoom = request.GET['zoom']
    
    #lat_lon = request.GET['ll']
    #north_east = request.GET['ne']
    #like = request.GET['lk']
    #like_low = request.GET['lk_l']
    #like_high = request.GET['lk_h']

  except:
    context = {
            #same
              'pos_data': json.dumps(positions),
              'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
              'siteslist': json.dumps(sites),
              'form': Form(),

            #unique to except (if no form data was entered
              'message': "ERROR: Please select a data type, transmitter, and date range.",
              }

    return render(request, 'maps4.html', context)
  
  else:
    #if form.is_valid():
    dt_fr_sec = time.mktime(datetime.datetime.strptime(dt_fr,
                '%Y-%m-%d %H:%M:%S').timetuple())
    dt_to_sec = time.mktime(datetime.datetime.strptime(dt_to,
                '%Y-%m-%d %H:%M:%S').timetuple())
     
    pos_filtered_list = []
    pos_query = Position.objects.filter(timestamp__gte = dt_fr_sec, timestamp__lte= dt_to_sec, depID=tx)
    
    for p in pos_query:
      (lat, lon) = utm.to_latlon(float(p.easting), 
                  float(p.northing),
                  p.utm_zone_number,
                  p.utm_zone_letter)
      pos_filtered_list.append((p.ID, p.depID, float(p.timestamp), 
                      float(p.easting), float(p.northing),
                      p.utm_zone_number, #p.utm_zone_letter,
                      float(p.likelihood), float(p.activity),
                      (lat, lon)))
    
    context = {
          #same
            'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
            'pos_data': json.dumps(pos_filtered_list),
            'siteslist': json.dumps(sites),
            'form': Form(request.GET or None),

          #unique to else (if form data was entered)
            'tx': json.dumps(tx),
            'data_type': json.dumps(data_type),
            'dt_fr': dt_fr_sec,
            'dt_to': dt_to_sec,
            'zoom': json.dumps(zoom),

            }

    return render(request, 'maps4.html', context)


#------------------- end of maps4 class----------------

def maps3(request):
  context = {}
  return render(request, 'maps3.html', context)
