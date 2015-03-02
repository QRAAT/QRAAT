# Test code for position estimation. To run, you'll need the following
# Python packages:
#  utm, numdifftools (available through pip)
#  numpy, scipy, matplotlib 

import signal1, position1

cal_id = 3   # Calibration ID, specifies steering vectors to use. 
dep_id = 105 # Deployment ID, specifies a transmitter. 

# siteID -> UTM position, known positions of sites for source
# localization. The real component is northing, the imaginary
# component is easting. 
sites = {2 : (4261604.51+574239.47j), # site2
         3 : (4261569.32+575013.86j), # site10
         4 : (4260706.17+573882.15j), # site13
         5 : (4260749.75+575321.92j), # site20
         6 : (4260856.82+574794.06j), # site21
         8 : (4261100.56+574000.17j)  # site39
         }
         
# UTM position, initial guess of position.
center = (4260500+574500j) 

zone = (10, 'S') # UTM zone.

# Read steering vectors from file.
sv = signal1.SteeringVectors.read(cal_id)


def real_data():

  # Read signal data, about an hour's worth.
  sig = signal1.Signal.read(sites.keys())

  # Estimate position using all data. To use the MLE instead 
  # of Bartlet's, do `method=signal1.Signal.MLE`. 
  #pos = position1.PositionEstimator(dep_id, sites, center, sig, sv,
  #                method=signal1.Signal.Bartlet)
  positions = position1.WindowedPositionEstimator(dep_id, sites, center, sig, sv, 
                  60 * 5, 30, method=signal1.Signal.Bartlet)

  
  # Plot position and search space. 
  for i, pos in enumerate(positions): 
    pos.plot('%d.png' % (i), sites, center, 10, 150)


def sim_data():

  # Simpulate signal given known position p.  
  p = center + complex(650,0)

  # Noise paramters. 
  # Signal to noise ratio 
  sig_t = 1
  sig_n = 1 
  sig = signal1.IdealSimulator(p, sites, sv, sig_n, sig_t, 10)
  (sig_n, sig_t) = sig.estimate_var()
  print "sig_n"
  for (id, (a, b)) in sig_n.iteritems():
    print id, '%0.5f %0.5f' % (a.real, b)
  print "sig_t"
  for (id, (a, b)) in sig_t.iteritems():
    print id, '%0.5f %0.5f' % (a.real, b)

  pos = position1.PositionEstimator(999, sites, center, 
                               sig, sv, method=signal1.Signal.MLE)
  pos.plot('fella.png', sites, center, 10, 150, p)
 
  conf = position1.ConfidenceRegion(pos, sites, 0.683) 
  conf.display(p)  
  if p in conf: print 'Yes!' 
  else: print 'no.'
  
'''

  Notes:

  Intuitively, the size of the confidence interval should scale with 
  the SNR. 


'''

# Testing, testing .... 
sim_data()
