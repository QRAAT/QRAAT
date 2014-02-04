#!/usr/bin/python
# Run these programs with various experiments.
import sys, os, re, time


progs={ "pos" : "rmg_position", 
        "ll" : "plot_ll.py", 
        "search_space" : "plot_search_space.py" }

                # t_start,           t_end,             tx_id, t_win, t_step
exps={ "feb2" : ( 1391390700.638165, 1391396399.840252, 54,    30,    120),  
       "cal" :  ( 1376420800.0     , 1376442000.0     , 51,    30,    120) }

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
      
      fn = progs[sys.argv[1]]
      (t_start, t_end, tx_id, t_win, t_step) = exps[sys.argv[2]]
      res = os.system(("/usr/bin/python {0} " 
        "--t-start={1} --t-end={2} " 
        "--t-win={3} --t-delta={4} --tx-id={5}").format(fn, 
                                                  t_start, t_end,
                                                  t_win, t_step, 
                                                  tx_id))

      if sys.argv[1] == 'pos': # Output the positions added to DB. 
        os.system("mysql -u reader -B -e \"SELECT * FROM qraat.Position\"")
        
 
  
  else: die("unknown prog")
    

else: die("not enough arguments")

