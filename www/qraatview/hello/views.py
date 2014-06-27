# views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
import qraat, time, datetime, json, utm
from hello.maps import Convert
from hello.models import Position, tx_ID, track, sitelist

def maps4(request):
  
  positions = []
  for p in Position.objects.all()[:5000]:
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
    sites.append((s.ID, s.name, s.location, float(s.latitude),
                  float(s.longitude), float(s.easting), 
                  float(s.northing), s.utm_zone_number, s.rx))

  try:
    tx = request.GET['tx_ID']
    data_type = request.GET['data_type']
    dt_fr = request.GET['dt_fr']
    dt_to = request.GET['dt_to']

  except:
    context = {
            #same
              'pos_data': json.dumps(positions),
              'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
              'sites': json.dumps(sites),

            #unique to except (if no form data was entered
              'message': "Select your preferences.",

              }

    return render(request, 'maps4.html', context)
  
  
  else:
    dt_fr_sec = time.mktime(datetime.datetime.strptime(dt_fr,
                '%Y-%m-%d %H:%M:%S').timetuple())
    dt_to_sec = time.mktime(datetime.datetime.strptime(dt_to,
                '%Y-%m-%d %H:%M:%S').timetuple())

    context = {
          #same
            'tx_IDs': tx_ID.objects.order_by('-active', 'ID').all(),
            'pos_data': json.dumps(positions),
            'sites': json.dumps(sites),

          #unique to else (if form data was entered)
            'tx': tx,
            'data_type': data_type,
            'dt_fr': dt_fr_sec,
            'dt_to': dt_to_sec,
            }

    return render(request, 'maps4.html', context)


#------------------- end of maps4 class----------------


def list(request):
  context = {'siteList': Site.sites,
              'staticvar': Site.static_pyth_var,
              'jsonvarpy': Site.jsonvarpy,
              'site_list_length': Site.site_list_length
            }
  return render(request,'list.html', context)

def maps3(request):
  context = {}
  return render(request, 'maps3.html', context)
