# File: models.py

from django.db import models, connection
from django.core import serializers
from django.forms import ModelForm
from django import forms
from django.core.serializers.json import DjangoJSONEncoder

import json
import qraat
import time
import datetime
import utm

class Prefs(models.Model):
  db = models.CharField(max_length=8)
  dtfr = models.DateField(blank=True, null=True)
  tifr = models.TimeField(blank=True, null=True)
  dtto = models.DateField(blank=True, null=True)
  tito = models.TimeField(blank=True, null=True)

  def __unicode__(self):
    return self.db


class Convert(models.Model):
#list of tuples: latlons_pos
  cursor2 = connection.cursor()
  cursor2.execute("SELECT ID, depID, timestamp, easting, northing, utm_zone_number, utm_zone_letter, likelihood, activity FROM qraat.Position limit 2000")
  poslist_rows = cursor2.fetchall()
  latlons_pos = []
  for (s, d, t, easting, northing, number, letter, l, a) in poslist_rows:
    (lat, lon) = utm.to_latlon(float(easting), float(northing), number, letter)
    latlons_pos.append((lat, lon))

  json_pos = json.dumps(latlons_pos)
  pos_list_len = json.dumps(len(latlons_pos))

#complete list of data from the Position table
  data_list = []
  for (ID, depID, timestamp, easting, northing, utm_zone_number, utm_zone_letter, likehood, activity) in poslist_rows:
  #note: don't put in utm_zone_letter because it serializes weird
    (latitude, longitude) = utm.to_latlon(float(easting), float(northing), number, letter)
    #datetime_raw = time.localtime(timestamp)
    #datetime = time.strftime('%Y-%m-%d %H:%M:%S', datetime_raw)
    data_list.append((ID, depID, float(timestamp), float(easting), float(northing), utm_zone_number, float(likehood), float(activity), (latitude, longitude)))
    
  
  # need to serialize decimal timestamp OR make it a float? does the lat and lon work?
  json_data_list = json.dumps(data_list)
  data_list_len = json.dumps(len(data_list))


#transmitter list

  cursor3 = connection.cursor()
  cursor3.execute("SELECT ID, tx_info_ID, active FROM qraat.tx_ID order by active desc, ID asc")
  tx_rows = cursor3.fetchall()
  tx_list = []
  for (txid, info, active) in tx_rows:
    tx_list.append((txid, info, active))

  json_tx = json.dumps(tx_rows)



#to do:
#dynamic, pass in from forms:
#change Table (track vs Position)
#filter by time


  #this works for getting the list of tuples of sitelists
  '''
  cursor = connection.cursor()
  cursor.execute("SELECT easting, northing, utm_zone_letter, utm_zone_number FROM qraat.sitelist")
  sitelist_rows = cursor.fetchall()
  latlons = []
  for (easting, northing, letter, number) in sitelist_rows:
    (lat, lon) = utm.to_latlon(float(easting), float(northing), number, letter)
    latlons.append((lat, lon))
    '''
  #this is just for templates:
  #latlons_dict = dict(latlons)


              #-- CHECK TO SEE IF DIF DATABASES WORK --
#if request.GET['db'] == "sitelist":
  #cursor.execute("SELECT easting, northing, utm_zone_letter, utm_zone_number FROM qraat.sitelist")
#else if request.GET['db'] == "Position":
  #cursor.execute("SELECT easting, northing, utm_zone_letter, utm_zone_number FROM qraat.sitelist")
# else:
  #cursor.execute("SELECT easting, northing, utm_zone_letter, utm_zone_number FROM qraat.track")


              #----DYNAMIC -----
# pref_db = request.GET['db']
# sql_command = "SELECT easting, northing, utm_zone_letter, utm_zone_number FROM qraat."
#sql_command.append += pref_db



class Site(models.Model):
  db_con = qraat.util.get_db('reader')
  sites = qraat.csv(db_con=db_con, db_table='sitelist')

  static_pyth_var = 45

  cursor = connection.cursor()
  cursor.execute("SELECT easting, northing, utm_zone_letter,utm_zone_number FROM qraat.sitelist")
  sitelist_rows = cursor.fetchall()
  latlons = []
  for (easting, northing, letter, number) in sitelist_rows:
    (lat, lon) = utm.to_latlon(float(easting), float(northing), number, letter)
    latlons.append((lat, lon))

    jsonvarpy = json.dumps(latlons)
 
    site_list_length = json.dumps(len(latlons))


class LatLng(models.Model):
  #def __unicode__(self):
  #  return '%f, %f' % (self.lat, self.lng)
  lat = models.FloatField(max_length=50)
  lng = models.FloatField(max_length=50)

class Poll(models.Model):
  def __unicode__(self):
    return self.question
  def was_published_today(self):
    return self.pub_date.date() == datetime.date.today()
  question = models.CharField(max_length=200)
  pub_date = models.DateTimeField('date published')

class Choice(models.Model):
 def __unicode__(self):
    return self.choice
 poll = models.ForeignKey(Poll)
 choice = models.CharField(max_length=200)
 votes = models.IntegerField()

#class Map(models.Model):
#  def __unicode__(self):
#    return self.choice
#lat = models.IntegerField()
#lng = models.IntegerField()
