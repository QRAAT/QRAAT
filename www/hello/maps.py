# File: maps.py 

from django.db import models, connection
from django.core import serializers
from django.forms import ModelForm
from django import forms
from django.core.serializers.json import DjangoJSONEncoder


import json, qraat, time, datetime, utm, sys, qraat.srv, MySQLdb as mdb

class Convert:

#!/usr/bin/python
  try: 
    start = time.time()
    print "template: start time:", time.asctime(time.localtime(start))
    db_con5 = qraat.util.get_db('reader')
                                        # trackID, t_start, t_end
    track = qraat.srv.track.Track(db_con5, 0, 1376420800, 1376442000) 
    
    #for pos in track:
    #  print pos
      #outputs --> 0: ID, 1: dep_ID, 2: timestamp 3: easting, 4: northing, 5: number, 6: letter, 7: likelihood 8: activity
        #(32742L, 77L, 1376433897.0, 574441.13, 4259698.55, 10, 'S', 211.199601, 0.972890572988)
        #(32742L, 73L, 1376433897.0, 574441.13, 4259698.55, 10, 'S', 211.199601, 0.972890572988)
        #etc
    
  except mdb.Error, e:
    print >>sys.stderr, "template: error: [%d] %s" % (e.args[0], e.args[1])
    sys.exit(1)

  except qraat.error.QraatError, e:
    print >>sys.stderr, "template: error: %s." % e

  finally: 
    print "template: finished in %.2f seconds." % (time.time() - start)
    
    track_list = []
    for i in track:
      track_list.append(i)
