# Time filter. This program attempts to remove false positives from 
# the pulse data based on the rate at which the transmitter emits 
# pulses. Neighboring points are used to coraborate the validity of
# a given point. This is on a per transmitter per site basis; a 
# useful extension to this work will be to coroborate points between
# sites.

import sys
import qraat
import numpy as np
import MySQLdb as mdb

# Constants and parameters for per site/transmitter pulse filtering. 

# Some constants. 
PARAM_BAD = -1
BURST_BAD = -2 

# Some parameters. 
BURST_INTERVAL = 10      # seconds
BURST_THRESHOLD = 20     # pulses/second
SCORE_INTERVAL = 60 * 5  # seconds
SCORE_ERROR = 0.2        # seconds

# Factor by which to multiply timestamps.
TIMESTAMP_PRECISION = 1000
                          


def get_score_intervals(t_start, t_end): 
  ''' Return a list of scoring windows given arbitrary start and finish. '''  
  
  intervals = range(t_start - (t_start % SCORE_INTERVAL), 
                    t_end + (t_end % SCORE_INTERVAL),
                    SCORE_INTERVAL)
                    
  for i in range(1,len(intervals)): 
    yield (intervals[i-1], intervals[i])


def get_interval_data(db_con, dep_id, site_id, interval):
  ''' Get pulse data for interval. 
  
    Last columns are for the absolute and relative scores of the
    record. (X[:,5] and X[:,6] resp.) Initially, there values are 0. 
  ''' 

  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, band3, band10, 0, 0 
                   FROM est
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp < %s
                    AND siteID = %s
                  ORDER BY timestamp''', 
                (dep_id, interval[0], interval[1], site_id,))
 
  data = []
  for row in cur.fetchall():
    data.append(list(row))
    data[-1][2] = int(data[-1][2] * TIMESTAMP_PRECISION)
  
  return np.array(data, dtype=np.int)


def get_tx_params(db_con, dep_id): 
  ''' Get transmitter parameters for band filter as a dictionary.
    
    `band3` and `band10` are expected to be among the tramsitter's 
    paramters and converted to integers. If they're unspecified (NULL), 
    they are given `sys.maxint`. All other paramters are treated as 
    strings.
  ''' 

  cur = db_con.cursor()
  cur.execute('''SELECT param.name, param.value
                   FROM tx_parameters AS param
                   JOIN tx ON tx.ID = param.txID
                  WHERE tx.ID = (SELECT tx.ID FROM tx
                                   JOIN deployment ON tx.ID = deployment.txID
                                  WHERE deployment.ID = %s)''', (dep_id,))
  
  params = {} 
  for (name, value) in cur.fetchall(): 
    if name == 'band3': 
      if value == '':
        params['band3'] = sys.maxint
      else: 
        params['band3'] = int(value)
    
    elif name == 'band10': 
      if value == '':
        params['band10'] = sys.maxint
      else: 
        params['band10'] = int(value)

    else: 
      params[name] = value

  return params



def expected_pulse_interval(data): 
  ''' Compute expected pulse rate over data.
  
    Data is assumed to be sorted by timestamp and timestamps should be
    multiplied by `TIMESTAMP_PRECISION`. (See `get_interval_data()`.)  
  ''' 
  
  (rows, cols) = data.shape
  
  # Compute pairwise time differentials. 
  diffs = []
  for i in range(rows):
    for j in range(i+1, rows): 
      diffs.append(data[j,2] - data[i,2])

  # Create a histogram. Bins are scaled by `SCORE_ERROR`. 
  (hist, bins) = np.histogram(diffs, bins = (max(data[:,2]) - min(data[:,2]))
                                        / (SCORE_ERROR * TIMESTAMP_PRECISION))
  
  i = np.argmax(hist)

  #print "Expected pulse interval is %.2f seconds" % ((bins[i] + bins[i+1])
  #                                            / (2 * TIMESTAMP_PRECISION))
  
  return int(bins[i] + bins[i+1]) / 2
  

def parametric_filter(data, tx_params): 
  ''' Parametric filter. Set score to `PARAM_BAD`.

    So far we only look at `band3` and `band10`. 
  '''

  (rows, _) = data.shape
  for i in range(rows): 
    if data[i,3] > tx_params['band3'] or data[i,4] > tx_params['band10']:
      data[i,5] = PARAM_BAD

  return data[np.where(data[:,5] != PARAM_BAD)]


def burst_filter(data, interval): 
  ''' Burst filter. Set score to `BURST_BAD`.
    
    Remove segments of points whose density exceed the a priori 
    pulse rate by an order of magnitude. For now, it is assumed
    that no transmitter produces more than two pulses a second. 
    Note that we could eventually use the 'pulse_rate' parameter
    in `qraat.tx_parameter`. 
  ''' 

  # Create histogram of pulses with `BURST_INTERVAL` second bins. 
  (hist, bins) = np.histogram(data[:,2], 
                              range = (interval[0] * TIMESTAMP_PRECISION, 
                                       interval[1] * TIMESTAMP_PRECISION),
                              bins = SCORE_INTERVAL / BURST_INTERVAL)
  
  # Find bins with bursts. 
  bad_intervals = []
  for i in range(len(hist)): 
    #print "%d pulses from %.2f to %.2f." % (hist[i], 
    #                float(bins[i]) / TIMESTAMP_PRECISION, 
    #                float(bins[i+1]) / TIMESTAMP_PRECISION)
    if (float(hist[i]) / BURST_INTERVAL) > BURST_THRESHOLD: 
      bad_intervals.append((bins[i], bins[i+1]))
      # TODO If it were possible to carry around the row index when
      # computing the histogram, we could mark signals within bad 
      # bins here. 

  # Mark signals within bad bins. 
  (rows, _) = data.shape
  for i in range(rows): 
    for (t0, t1) in bad_intervals:
      if t0 <= data[i,2] and data[i,2] <= t1:
        data[i,5] = BURST_BAD

  return data[np.where(data[:,5] != BURST_BAD)]


def time_filter(data, interval):
  ''' Time filter. Set score absolute score and normalize. ''' 

  pulse_interval = expected_pulse_interval(data)
  









if __name__ == '__main__': 
  db_con = qraat.util.get_db('writer')
  dep_id = 51; site_id = 2; 
  t_start, t_end = 1376427421, 1376434446

  tx_params = get_tx_params(db_con, dep_id)

  for interval in get_score_intervals(t_start, t_end):
    data = get_interval_data(db_con, dep_id, site_id, interval)
    data = parametric_filter(data, tx_params)
    data = burst_filter(data, interval)
    time_filter(data, interval)
