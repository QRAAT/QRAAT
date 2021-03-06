#!/usr/bin/env python2
# Run these programs with various experiments.
import sys, os, re, time


progs={ "pos" : "../pos/rmg_position", 
        "ll" : "plot_ll.py", 
        "search_space" : "plot_search_space.py", 
        "track" : "plot_track.py" }

exps = {         # t_start,           t_end,             tx_id, t_win, t_step
       "feb2"  : ( 1391390700.638165, 1391396399.840252, 54,    30,    5),  
       "oops"  : ( 1391390700, 1391396399.840252 + 3600 * 6, 54,    30,    5),  
       "short" : ( 1376420800.0     , 1376427800.0     , 51,    30,    120),  
       "cal"   : ( 1376420800.0     , 1376442000.0     , 51,    30,    5),
       'all'   : ( 0                , 2000000000       , 60,    30,  30), 
       
       '57' : ( 1382252400       , 1382598000       , 57,    30, 5),
       '58' : ( 1389859200       , 1390204800       , 58,    30, 5)       
       }

def die(msg):
  print >>sys.stderr, "error: %s. (-h for help.)" % msg
  print >>sys.stderr, "usage: run <prog> <experiment>  -OR- "
  print >>sys.stderr, "       run <prog> --t-start=\"YYYYMMDD HHMM\" --t-end=\" ... \"]"
  sys.exit(1)

def help():
  print "Possible program choices:    %s" % progs.keys()
  print "Possible experiment choices: %s" % exps.keys()
  sys.exit(0)


if len(sys.argv) >= 3: 
  
  if sys.argv[1] == '-h': help()
  
  elif sys.argv[1] in progs.keys(): 
    
    if sys.argv[2] in exps.keys(): 

      if sys.argv[1] == 'track':
        
        fn = progs[sys.argv[1]]
        (t_start, t_end, tx_id, t_win, t_step) = exps[sys.argv[2]]
        res = os.system(("/usr/bin/python {0} " 
          "--t-start={1} --t-end={2} --tx-id={3}").format(fn, 
                                                    t_start, t_end,
                                                    tx_id))
      
      else:

        fn = progs[sys.argv[1]]
        (t_start, t_end, tx_id, t_win, t_step) = exps[sys.argv[2]]
        res = os.system(("/usr/bin/python {0} " 
          "--t-start={1} --t-end={2} --tx-id={3} "
          "--t-delta={3} --t-window={4}" ).format(fn, 
                                                    t_start, t_end,
                                                    tx_id, t_step, t_win))

        if sys.argv[1] == 'pos': # Output the positions added to DB. 
          pass#os.system("mysql -u reader -B -e \"SELECT * FROM qraat.Position\"")
        
 
  
  else: die("unknown prog")
    

else: die("not enough arguments")

