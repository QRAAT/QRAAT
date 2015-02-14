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
sites = {2 : (4261604.51+574239.47j), 
         3 : (4261569.32+575013.86j), 
         4 : (4260706.17+573882.15j), 
         5 : (4260749.75+575321.92j), 
         6 : (4260856.82+574794.06j), 
         8 : (4261100.56+574000.17j)} 
         
# UTM position, initial guess of position.
center = (4260500+574500j) 

zone = (10, 'S') # UTM zone.

# Read steering vectors from file.
sv = signal1.SteeringVectors.read(cal_id)

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