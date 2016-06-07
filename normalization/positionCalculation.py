import qraatSignal
import MySQLdb
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
import numpy as np
import time
    

def compute_bearing_spline(l): 
  ''' Interpolate a spline on a bearing likelihood distribuiton. 
    
    Input an aggregated bearing distribution, e.g. the output of 
    `aggregate_spectrum(p)` where p is the output of `_per_site_data.mle()` 
    or `_per_site_data.bartlet()`.
  '''
  bearing_domain = np.arange(-360,360)       
  likelihood_range = np.hstack((l, l))
  return spline1d(bearing_domain, likelihood_range)


def compute_likelihood_grid(sites, splines, center, scale, half_span):
  ''' Compute a grid of candidate points and their likelihoods. '''
  # Generate a grid of positions with center at the center. 
  positions = np.zeros((half_span*2+1, half_span*2+1), np.complex)
  
  for e in range(-half_span,half_span+1):
    for n in range(-half_span,half_span+1):
      positions[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)
  # Compute the likelihood of each position as the sum of the likelihoods 
  # of bearing to each site. 
  likelihoods = np.zeros(positions.shape, dtype=float)
  for siteID in splines.keys():
    bearing_to_positions = np.angle(positions - sites[siteID]) * 180 / np.pi
    try:
      spline_iter = iter(splines[siteID])
    except TypeError:
      likelihoods += splines[siteID](bearing_to_positions.flat).reshape(bearing_to_positions.shape)
    else:
      for s in spline_iter:
        likelihoods += s(bearing_to_positions.flat).reshape(bearing_to_positions.shape)
  return (positions, likelihoods)

def positionCalculate(deploymentID, start_time, end_time, siteIDs, normalized):
  ''' the position is calculated in a 240m by 240m grid with 0.5m intervals'''
  initTime = time.time()
  
  half_span = 240
  sites = {2:np.complex(4261604.51, 574239.47),
           11:np.complex(4261812.89, 573661.44),
           12:np.complex(4262083.76, 573527.01),
           13:np.complex(4262135.31, 573823.12)}

  center = np.complex(4261870, 573723)
  bearing = {2:[],11:[],12:[],13:[]}
  
  #loading the bearings into memory
  for i in bearing:
    fileName = 'deployment %s - site %s.txt'%(deploymentID, i)
    with open(fileName) as f:
      for line in f:
        bearing[i].append(np.array(map(float,line.split(','))))

  if deploymentID == 142:
    timeInterval = 1
  else:
    timeInterval = 15
  halfWindow = 15
  for i in range(start_time + timeInterval, end_time + 1, timeInterval):
    weightedBearing = {2:np.zeros(360), 11:np.zeros(360),
                        12:np.zeros(360), 13:np.zeros(360)}
    
    for j in bearing:
      idx = 1
      for k in bearing[j]:
        if (k[0] < i - halfWindow):
          bearing[j].pop(0)
        elif (k[0] <= i + halfWindow):
          idx += 1
        else:
          break
      try:
        weightedBearing[j] = sum(bearing[j][:idx])[1:]
        #this normalize by sites
        if normalized:
          weightedBearing[j] /= sum(weightedBearing[j])
      except TypeError:
        pass

    #finding number of sites within this time window
    numSites = 0
    for x in weightedBearing:
      if sum(weightedBearing[x]) != 0:
        numSites += 1

    splines = {}
    for j in weightedBearing:
      splines[j] = compute_bearing_spline(weightedBearing[j])
    
    p, l = compute_likelihood_grid(sites, splines, center, 0.5, half_span)
    maxIdx = np.argmax(l)
    mostLikelyPosition = p.flat[maxIdx]
    db_con = MySQLdb.connect(user="root", db="qraat")
    cur = db_con.cursor()
    cur.execute("""
                 INSERT INTO position_non_normalized
                 (deploymentID, timestamp, easting, northing,
                 likelihood, numSites, isNormalized)
                 VALUES (%s, %s, %s, %s, %s, %s, %s);
              """%(deploymentID, i, mostLikelyPosition.imag,
                   mostLikelyPosition.real, l.flat[maxIdx],
                   numSites, normalized))
  
  print 'Took %s seconds.'%(time.time()-initTime)


def main():
  start_time = {142:1461884300,
                116:1435782759}
  end_time = {142:1461886955,
              116:1436713781}
  sites = {142:[2,11,12,13],
           116:[2,11,12,13]}
  
  for i in [142, 116]:
    for j in [0,1]:
      positionCalculate(i, start_time[i], end_time[i], sites[i], j)
  
  
if __name__ == '__main__':
  main()
