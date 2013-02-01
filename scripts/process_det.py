#!/usr/bin/env python
#commandline access to produce .est, .csv files from .det files
#called from proc_det.sh shell script
#Use: ./process_det.py det_directory_name est_directory_name csv_directory_name
#if there isn't all three arguments the script exits without doing anything


from rmg.est_dict import est_dict
import sys
if len(sys.argv) > 3:
  det_dirname = sys.argv[1]
  est_dirname = sys.argv[2]
  csv_dirname = sys.argv[3]
  est = est_dict()
  est.read_dir(det_dirname)
  est.write_est(est_dirname)
  est.write_csv(csv_dirname)
else:
  print "Not enough arguments.  Use is #process_det.py det_directory est_directory csv_directory"

