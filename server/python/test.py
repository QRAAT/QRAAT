# Test code for position estimation. To run, you'll need the following
# Python packages:
#  utm, numdifftools (available through pip)
#  numpy, scipy, matplotlib 

import signal1, position1
import util

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
db_con = util.get_db('reader')
sv = signal1.SteeringVectors(db_con, cal_id)


def real_data():

  # Read signal data, about an hour's worth.
  sv = signal1.SteeringVectors.read(3, 'sample/sv')
  sig = signal1.Signal.read(sites.keys(), 'sample/sig')
  

  # Estimate position using all data. To use the MLE instead 
  # of Bartlet's, do `method=signal1.Signal.MLE`. 
  pos = position1.PositionEstimator(dep_id, sites, center, sig, sv,
                  method=signal1.Signal.Bartlet)
  
  print pos.p
  pos.plot('yeah.png', sites, center)
  


def sim_data():

  # Simpulate signal given known position p.  
  p = center + complex(650,0)
  include = [2,3,5,4,6,8]

  sig_n = 0.002 # noise
  rho = signal1.scale_tx_coeff(p, 1, sites, include)
  sv_splines = signal1.compute_bearing_splines(sv)
  sig = signal1.Simulator(p, sites, sv_splines, rho, sig_n, 10, include)
    
  (sig_n, sig_t) = sig.estimate_var()

  pos = position1.PositionEstimator(999, sites, center, 
                               sig, sv, method=signal1.Signal.Bartlet)
  pos.plot('fella.png', sites, center, p)
 
  level=0.95
  position1.BootstrapCovariance(pos, sites).conf(level).display(p)
  position1.Covariance(pos, sites, p_known=p).conf(level).display(p)
  print position1.Covariance(pos, sites, p_known=p).conf(level).eccentricity()


# Testing, testing .... 
sim_data()
