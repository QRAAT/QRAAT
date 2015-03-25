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
sv = signal1.SteeringVectors.read(cal_id, 'sample/sv')


def real_data():

  # Read signal data, about an hour's worth.
  sig = signal1.Signal.read(sites.keys(), 'sample/sig')

  # Estimate position using all data. To use the MLE instead 
  # of Bartlet's, do `method=signal1.Signal.MLE`. 
  #pos = position1.PositionEstimator(dep_id, sites, center, sig, sv,
  #                method=signal1.Signal.Bartlet)
  #positions = position1.WindowedPositionEstimator(dep_id, sites, center, sig, sv, 
  #                60 * 5, 30, method=signal1.Signal.Bartlet)

  pos = position1.PositionEstimator(dep_id, sites, center, sig, sv,
                  method=signal1.Signal.Bartlet)
  print pos.p
  pos.plot('yeah.png', sites, center, 10, 150)
  
  # Plot position and search space. 
  #for i, pos in enumerate(positions): 
  #  pos.plot('%d.png' % (i), sites, center, 10, 150)


def sim_data():

  # Simpulate signal given known position p.  
  p = center + complex(650,0)

  rho = 1   # signal
  sig_n = 0.002 # noise
  sig = signal1.Simulator(p, sites, sv, rho, sig_n, 3, include=[2,3,5,4,6,8])
  (sig_n, sig_t) = sig.estimate_var()

  pos = position1.PositionEstimator(999, sites, center, 
                               sig, sv, method=signal1.Signal.Bartlet)
  #pos.plot('fella.png', sites, center, 10, 150, p)
 
  conf = position1.BootstrapConfidenceRegion(pos, sites, 0.90) 
  
  conf.display(p) 
  if p in conf: print 'Yes!' 
  else: print 'no.'
  print conf.e.area()
  

'''

  Notes:

  Intuitively, the size of the confidence interval should scale with 
  the SNR. 


'''

# Testing, testing .... 
sim_data()
