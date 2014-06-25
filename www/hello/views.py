#File: views.py

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from hello.models import Site, Poll, Choice, LatLng, Convert
#from hello.forms import LatLngForm
import qraat
import time, datetime

#def filter(request):
#  try:
#    mydat = request.GET['dat']
#    d = 
#  except:
#    context = {"message": "Please select a database name"}
#    return render(request, 'maps3.html', context)
#  else:
#    context = {'database': mydat}


# this is not used yet? but will be for prefs
def prefs(request):
  #form = MyForm(request.POST or None)
  #  if form.is_valid():
  #    do_x() #custom stuff
  #    return redirect('maps4.html')
  #  return render(request, maps4.html, {'form': form}) 
  
#  if request.method == 'GET':
#    form = PrefsForm(request.GET)
#    if form.is_valid():
#      form.save(commit=True)
#      return index(request)
#    else:
#      print form.errors
#  else:
#    form = PrefsForm()
#  return render_to_response('maps4.html', {'form': form}, context)


  try:
    db = request.GET['db']
    #dtfr = request.GET['dtfr']
    #tifr = request.GET['tifr']
    #dtto = request.GET['dtto']
    #tito = request.GET['tito']
  except:
    context = {"message": "Select your preferences."}
    return render(request, 'maps4.html', context)
  else:
    context = {
#  
#something is wrong here with the _texts            
            
           # "pref_text": "Preferences",
           # "db_text": "<br />Database: ",
            "db": db,
           # "dtfr_text": "<br />Date from: ",
           # 'dtfr': dtfr,
           # 'tifr_text': "<br />Time from: ",
           # 'tifr': tifr,
           # 'dtto_text': "<br />Date from: ",
           # 'dtto': dtto, 
           # 'tito_text': "<br />Time to: ",
           # 'tito': tito
            }
  return(request, 'maps4.html', context)


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
            }
    return render(request, 'maps4.html', context)

#the regular map
#
#def maps4(request):
#  context = {
#            'latlon': Convert.latlons_dict,
#            'latlon_list': Site.jsonvarpy,
#            'latlon_len': Site.site_list_length
#            }
#  return render(request, 'maps4.html', context)


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

#def maps(request):
#  return render_to_response('maps.html')

def maps2(request):
  return render_to_response('maps2.html')

def maps3(request):
  context = {'latlon': Convert.latlons_dict}
  return render(request, 'maps3.html', context)
  #return render_to_response('maps3.html')

def add(request):
  if request.method == 'POST':
    form = LatLngForm(request.POST)
    form.save()
    #if form.is_valid():
    #  form.save()

    try:
      lat = request.POST['lat']
      lng = request.POST['lng']
    except:
      context = {"message": "Enter a longitude and latitude"}
      return render(request, 'maps.html', context)
    else:
      context = {'latLngList': LatLng.objects.all(),
                  'form': LatLngForm(),
                  'lat': lat, 'lng': lng
                }
      return render(request, 'maps.html', context)
  else:
    context = {'form': LatLngForm()}
    return render(request, 'maps.html', context)

  #else:
  #  context = {'form': LatLngForm(), 'lat': lat, 'lng': lng }
  #  return render(request, 'maps.html', context)

#(request, poll_id):
#p = get_object_or_404(Poll, pk=poll_id)
#return render_to_response('hello/detail.html', {'poll': p}, context_ins    tance=RequestContext(request))

def index(request):
  latest_poll_list = Poll.objects.all().order_by('pub_date')[:5]
  return render_to_response('hello/index.html', {'latest_poll_list': latest_poll_list})
  
  #latest_poll_list = Poll.objects.all().order_by('pub_date')[:5]
  #t = loader.get_template('hello/index.html')
  #c = Context({
  #  'latest_poll_list': latest_poll_list,
  #})
  #return HttpResponse(t.render(c))
  
  #return HttpResponse("Hello,world. You're at the poll index.")

def detail(request, poll_id):
  p = get_object_or_404(Poll, pk=poll_id)
  return render_to_response('hello/detail.html', {'poll': p}, context_instance=RequestContext(request))
  
  #try:
  #  p = Poll.objects.get(pk=poll_id)
  #except Poll.DoesNotExist:
  #  raise Http404
  #return render_to_response('hello/detail.html', {'poll': p})
  
  #return HttpResponse("You're looking at poll %s." % poll_id)

def results(request, poll_id):
  return HttpResponse("You're looking at the results of poll %s." % poll_id)

def vote(request, poll_id):
  p = get_object_or_404(Poll, pk=poll_id)
  try:
    selected_choice = p.choice_set.get(pk=request.POST['choice'])
  except (KeyError, Choice.DoesNotExist):
    return render_to_response('hello/detail.html', {'poll': p, 'error_message': "You didn't select a choice.",},context_instance=RequestContext(request))
  else:
    selected_choice.votes += 1
    selected_choice.save()
    return HttpResponseRedirect(reverse('hello.views.results', args=(p.id,)))
  #return HttpResponse("You're voting on poll %s." % poll_id)

def results(request, poll_id):
  p = get_object_or_404(Poll, pk=poll_id)
  return render_to_response('hello/results.html', {'poll': p})
