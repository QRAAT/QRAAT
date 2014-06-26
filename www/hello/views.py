#File: views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from hello.maps import Site, Convert
#from hello.forms import LatLngForm
import qraat
import time, datetime


def maps4(request):
  
  try:
    tx = request.GET['tx_ID']
    data_type = request.GET['data_type']
    date_time = request.GET['datetime']
    #pref = request.GET['pref']
    #pref1 = request.GET['pref1']
    #pref2 = request.GET['pref2']
    #pref3 = request.GET['pref3']
  except:
    context = {
              "message": "Select your preferences.",
              #'latlon': Convert.latlons_dict,
              'latlon_list': Site.jsonvarpy,
              'latlon_len': Site.site_list_length,

              'latlon_pos': Convert.json_pos,
              'latlon_pos_len': Convert.pos_list_len,
              
              'json_data_list': Convert.json_data_list,
              'data_list_len': Convert.data_list_len,
              
              'tx_list': Convert.tx_list,
              #'tx_json': Convert.json_tx,

              'track_list': Convert.json_track,
              }
    return render(request, 'maps4.html', context)
  
  
  else:
    date_time_secs = time.mktime(datetime.datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S').timetuple())


    context = {
            'tx': tx,
            'data_type': data_type,
            'date_time': date_time_secs,
            #'pref': pref,
            #'pref1': pref1,
            #'pref2': pref2,
            #'pref3': pref3,
            
          #for the lines (positions)
            'latlon_pos': Convert.json_pos,
            'latlon_pos_len': Convert.pos_list_len,
            
          #for the site info
            'latlon_list': Site.jsonvarpy,
            'latlon_len': Site.site_list_length,
           
            'json_data_list': Convert.json_data_list,
            'data_list_len': Convert.data_list_len,  
 
          #transmitter list
            'tx_list': Convert.tx_list,
            'track_list': Convert.json_track,
            }

    return render(request, 'maps4.html', context)


def convert(request):
  context = {
  #'latlon': Convert.latlons_dict
  }
  return render(request, 'convert.html', context)

def list(request):
  context = {'siteList': Site.sites,
              'staticvar': Site.static_pyth_var,
              'jsonvarpy': Site.jsonvarpy,
              'site_list_length': Site.site_list_length
            }
  return render(request,'list.html', context)

def maps2(request):
  return render_to_response('maps2.html')

def maps3(request):
  context = {'latlon': Convert.latlons_dict}
  return render(request, 'maps3.html', context)
  #return render_to_response('maps3.html')

#def add(request):
#  if request.method == 'POST':
#    form = LatLngForm(request.POST)
#    form.save()
#    try:
#      lat = request.POST['lat']
#      lng = request.POST['lng']
#    except:
#      context = {"message": "Enter a longitude and latitude"}
#      return render(request, 'maps.html', context)
#    else:
#      context = {'latLngList': LatLng.objects.all(),
#                  'form': LatLngForm(),
#                  'lat': lat, 'lng': lng
#                }
#      return render(request, 'maps.html', context)
#  else:
#    context = {'form': LatLngForm()}
#    return render(request, 'maps.html', context)
#
