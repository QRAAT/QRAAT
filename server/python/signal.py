# Time filter. This program attempts to remove false positives from 
# the pulse data based on the rate at which the transmitter emits 
# pulses. Neighboring points are used to coraborate the validity of
# a given point. This is on a per transmitter per site basis; a 
# useful extension to this work will be to coroborate points between
# sites. 

# NOTE It would be nice if np.where() would return a shallow
#      copy. Then we could do 
#       time_filter(burst_filter(parametric_filter(data, _), _), _)

# NOTE The larger the score window, the more accurate we calculate 
#      the expected pulse interval.

# NOTE We don't yet account for the percentage of time the system is 
#      listening for the transmitter. This should be encorpoerated 
#      into the theoretical score over the pulse's neighborhood. 


import util
import sys
import numpy as np
import time

#### Constants and parameters for per site/transmitter pulse filtering. #######

# Burst filter parameters. 
BURST_INTERVAL = 10         # seconds
BURST_THRESHOLD = 20        # pulses/second

# Time filter paramters. 
SCORE_INTERVAL = 60 * 3     # seconds
SCORE_NEIGHBORHOOD = 20     # seconds

# Score error for pulse corroboration, as a function of the variation over 
# the interval. (Second moment of the mode pulse interval). These curves were 
# fit to a particular false negative / positive trade-off over a partitioned
# data set. See server/scripts/filter/test-data for details. 
SCORE_ERROR = lambda(x) : (-0.6324 / (x + 7.7640)) + 0.1255 # thresh = 0.2
#SCORE_ERROR = lambda(x) : 0.1956                           # thresh = 0.2

# Minumum percentage of transmitter's nominal pulse interval that the expected
# pulse_interval is allowed to drift. Tiny pulse intervals frequently result 
# from particularly noisy, but it may not be enough to trigger the burst 
# filter.
MIN_DRIFT_PERCENTAGE = 0.33

# Eliminate noisy intervals. 
MAX_VARIATION = 4


#### System parameters ... these shouldn't be changed. ########################

# Factor by which to multiply timestamps. 
TIMESTAMP_PRECISION = 1000

# Controls the number of bins in histograms. 
BIN_WIDTH = 0.02 

# Some constants. 
PARAM_BAD = -1
BURST_BAD = -2 

# Log output. 
VERBOSE = False

# Instrumentation accumulators
processing_time = {}
processing_time['setup'] = 0.0
processing_time['get_interval_data']=0.0
processing_time['expected_pulse_interval']=0.0
processing_time['param_filter']=0.0
processing_time['burst_filter']=0.0
processing_time['time_filter']=0.0
processing_time['update_data']=0.0
processing_time['update_intervals']=0.0

#### High level calls. ########################################################

def debug_output(msg): 
  if VERBOSE: 
    print "signal: %s" % msg

def Filter0(db_con, dep_id, site_id, t_start, t_end): 
  ''' Score points per site and transmitter, insert into database. 
  
    Return the number of pulses that were scored and the last id
    processed into the database.  
  '''   

  total = 0; max_id = 0
  tx_params = get_tx_params(db_con, dep_id)
  debug_output("depID=%d parameters: band3=%s, band10=%s, pulse_rate=%s" 
     % (dep_id, 'nil' if tx_params['band3'] == sys.maxint else tx_params['band3'],
                'nil' if tx_params['band10'] == sys.maxint else tx_params['band10'], 
                tx_params['pulse_rate']))
          
  interval_data = [] # Keep track of pulse rate of each window. 

  for interval in get_score_intervals(t_start, t_end):

    # Using overlapping windows in order to mitigate 
    # score bias on points at the end of the windows. 
    augmented_interval = (interval[0] - (SCORE_NEIGHBORHOOD / 2), 
                          interval[1] + (SCORE_NEIGHBORHOOD / 2))

    data = get_interval_data(db_con, dep_id, site_id, augmented_interval)
  
    if data.shape[0] == 0: # Skip empty chunks.
      debug_output("skipping empty chunk")
      continue

    debug_output("processing %.2f to %.2f (%d pulses)" % (interval[0], 
                                                          interval[1], 
                                                          data.shape[0]))
    
    parametric_filter(data, tx_params)
      
    if data.shape[0] >= BURST_THRESHOLD: 
      burst_filter(data, augmented_interval)

    # Tbe only way to coroborate isolated points is with other sites. 
    if data.shape[0] > 2:
      (pulse_interval, pulse_variation) = expected_pulse_interval({site_id : data}, tx_params['pulse_rate'])
      if pulse_interval > 0 and pulse_variation < MAX_VARIATION:
        time_filter(data, pulse_interval, pulse_variation)
        pulse_interval = float(pulse_interval) / TIMESTAMP_PRECISION
      else: pulse_interval = pulse_variation = None 

    else: pulse_interval = pulse_variation = None
    
    # When inserting, exclude overlapping points.
    (count, id) = update_data(db_con, 
       data[(data[:,2] >= (interval[0] * TIMESTAMP_PRECISION)) & 
            (data[:,2] <  (interval[1] * TIMESTAMP_PRECISION))])

    interval_data.append((interval[0], pulse_interval, pulse_variation))
  
    total += count
    max_id = id if max_id < id else max_id
  
  update_intervals(db_con, dep_id, site_id, interval_data)
  
  return (total, max_id)



def Filter(db_con, dep_id, t_start, t_end): 

  total_processing_timer_start = time.time()
  processing_timer_start = time.time()  
  total = 0; max_id = 0
  tx_params = get_tx_params(db_con, dep_id)
  debug_output("depID=%d parameters: band3=%s, band10=%s, pulse_rate=%s" 
     % (dep_id, 'nil' if tx_params['band3'] == sys.maxint else tx_params['band3'],
                'nil' if tx_params['band10'] == sys.maxint else tx_params['band10'], 
                tx_params['pulse_rate']))
  
  
  cur = db_con.cursor() 
  cur.execute('SELECT ID FROM site')
  sites = map(lambda(row) : row[0], cur.fetchall())

  processing_timer_stop = time.time()
  processing_time['setup'] += processing_timer_stop - processing_timer_start
  interval_data = {} # Keep track of pulse rate of each window. 
  for site_id in sites: 
    interval_data[site_id] = []

  cur.execute('CREATE TEMPORARY TABLE tempest AS SELECT ID, siteID, timestamp, band3, band10 FROM est WHERE deploymentID=%s AND timestamp > %s AND timestamp < %s', (dep_id, t_start - SCORE_NEIGHBORHOOD, t_end + SCORE_NEIGHBORHOOD))

  for interval in get_score_intervals(t_start, t_end):

    # Using overlapping windows in order to mitigate 
    # score bias on points at the end of the windows. 
    augmented_interval = (interval[0] - (SCORE_NEIGHBORHOOD / 2), 
                          interval[1] + (SCORE_NEIGHBORHOOD / 2))

    data = {}
    for site_id in sites: 
      data[site_id] = get_interval_data(db_con, dep_id, site_id, augmented_interval)
        
    (pulse_interval, pulse_variation) = expected_pulse_interval(data, tx_params['pulse_rate'])

    for site_id in sites:
      
      if data[site_id].shape[0] == 0: # Skip empty chunks.
        debug_output("siteID=%s: skipping empty chunk" % site_id)
        continue

      debug_output("siteID=%s: processing %.2f to %.2f (%d pulses)" % (site_id,
                                                                       interval[0], 
                                                                       interval[1], 
                                                                       data[site_id].shape[0]))
      
      parametric_filter(data[site_id], tx_params)
        
      if data[site_id].shape[0] >= BURST_THRESHOLD: 
        burst_filter(data[site_id], augmented_interval)

      # Tbe only way to coroborate isolated points is with other sites. 
      if data[site_id].shape[0] > 2 and pulse_interval > 0:
        time_filter(data[site_id], pulse_interval, pulse_variation)
      
      # When inserting, exclude overlapping points.
      (count, id) = update_data(db_con, 
         data[site_id][(data[site_id][:,2] >= (interval[0] * TIMESTAMP_PRECISION)) & 
                       (data[site_id][:,2] <  (interval[1] * TIMESTAMP_PRECISION))])

      interval_data[site_id].append((interval[0], float(pulse_interval) / TIMESTAMP_PRECISION, pulse_variation))
  
      total += count
      max_id = id if max_id < id else max_id
  
  for site_id in sites:
    update_intervals(db_con, dep_id, site_id, interval_data[site_id])
  
  total_processing_time = time.time() - total_processing_timer_start
  for k,v in processing_time.iteritems():
    print k,v,v/total_processing_time

  cur.execute("DROP TEMPORARY TABLE tempest")
  print 'total time', total_processing_time, total_processing_time/total_processing_time
  return (total, max_id)





#### Handle pulse data. ####################################################### 

def get_score_intervals(t_start, t_end): 
  ''' Return a list of scoring windows given arbitrary start and finish. '''  
 
  t_start = int(t_start); t_end = int(t_end)
  for i in range(t_start - (t_start % SCORE_INTERVAL), 
                 t_end   + (t_end   % SCORE_INTERVAL),
                 SCORE_INTERVAL):
    yield (i, i + SCORE_INTERVAL)


def get_interval_data(db_con, dep_id, site_id, interval):
  ''' Get pulse data for interval. 
  
    Last columns are for the score and theoretically best score of the
    record. (X[:,5], X[:,6] resp.) Initially, there values are 0. 
  ''' 

  processing_timer_start = time.time()

  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, band3, band10, 0, 0, 0  
                   FROM tempest
                   WHERE timestamp >= %s
                    AND timestamp < %s
                    AND siteID = %s
                  ORDER BY timestamp''', 
                (interval[0], interval[1], site_id,))
 
                  #WHERE deploymentID = %s
  #data = []
  #for row in cur.fetchall():
  #  data.append(list(row))
  #  data[-1][2] = int(data[-1][2] * TIMESTAMP_PRECISION)
  data = np.array(cur.fetchall(),dtype=float)
  if data.shape[0] > 0:
    data[:,2] *= TIMESTAMP_PRECISION
  processing_timer_stop = time.time()
  processing_time['get_interval_data'] += processing_timer_stop - processing_timer_start

 
  #return np.array(data, dtype=np.int64)
  return data

def update_data(db_con, data): 
  ''' Insert scored data, updating existng records. 
  
    Return the number of inserted scores and the maximum estID. 
  ''' 
 
  processing_timer_start = time.time()
 
  (row, _) = data.shape; 
  inserts = []#; deletes = []
  for i in range(row):
    inserts.append((data[i,0], data[i,5], data[i,6], data[i,7],data[i,0], data[i,5], data[i,6], data[i,7]))
    #deletes.append(data[i,0])

  cur = db_con.cursor()
  #cur.executemany('DELETE FROM estscore WHERE estID = %s', deletes)
  cur.executemany('INSERT INTO estscore (estID, score, theoretical_score, max_score) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE estID=%s, score=%s, theoretical_score=%s, max_score=%s', inserts)

  max_id = np.max(data[:,0]) if len(inserts) > 0 else 0

  processing_timer_stop = time.time()
  processing_time['update_data'] += processing_timer_stop - processing_timer_start

  return (len(inserts), max_id)


def update_intervals(db_con, dep_id, site_id, intervals):
  ''' Insert interval data for (dep, site). ''' 
 
  processing_timer_start = time.time()
 
  if len(intervals) > 0: 

    cur = db_con.cursor()
    cur.execute('''DELETE FROM estinterval 
                    WHERE timestamp >= %s 
                      AND timestamp <= %s
                      AND deploymentID = %s
                      AND siteID = %s''', 
              (intervals[0][0], intervals[-1][0], dep_id, site_id))

    inserts = []
    for (t, pulse_rate, pulse_variation) in intervals:
      inserts.append((dep_id, site_id, t, SCORE_INTERVAL, pulse_rate, pulse_variation))
      
    cur.executemany('''INSERT INTO estinterval (deploymentID, siteID, timestamp, 
                                                duration, pulse_interval, pulse_variation)
                             VALUE (%s, %s, %s, %s, %s, %s)''', inserts)
  processing_timer_stop = time.time()
  processing_time['update_intervals'] += processing_timer_stop - processing_timer_start



def get_tx_params(db_con, dep_id): 
  ''' Get transmitter parameters for band filter as a dictionary.
    
    `band3` and `band10` are expected to be among the tramsitter's 
    paramters and converted to integers. If they're unspecified (NULL), 
    they are given `sys.maxint`. `pulse_ratae` is interpreted as a float
    pulses / minute. All other paramters are treated as strings.
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

    elif name == 'pulse_rate': 
      params[name] = float(value)

    else: 
      params[name] = value

  return params



##### Per site/transmitter filters. ###########################################

def expected_pulse_interval(data_dict, pulse_rate): 
  ''' Compute expected pulse rate over data.
  
    Data is assumed to be sorted by timestamp and timestamps should be
    multiplied by `TIMESTAMP_PRECISION`. (See `get_interval_data()`.)  

    :param pulse_rate: Transmitter's nominal pulse rate in pulses / minute. 
  ''' 
 
  processing_timer_start = time.time()
 
  max_interval = ((60 * (2 - MIN_DRIFT_PERCENTAGE)) / pulse_rate) * TIMESTAMP_PRECISION
  min_interval = ((60 * MIN_DRIFT_PERCENTAGE) / pulse_rate) * TIMESTAMP_PRECISION
  bin_width = int(BIN_WIDTH * TIMESTAMP_PRECISION)

  # Compute pairwise time differentials. 
  diffs = []
  for (_, data) in data_dict.iteritems():
    if data.shape[0] > 0:
      (rows, cols) = data.shape
      for i in range(rows):
        for j in range(i+1, rows): 
          diff = data[j,2] - data[i,2]
          if min_interval < diff and diff < max_interval: 
            diffs.append(diff)

  if len(diffs) <= 2: 
    return (0, 0)

  # Create a histogram. Bins are scaled by `BIN_WIDTH`. 
  (hist, bins) = np.histogram(diffs, bins = 1 + ((max(diffs) - min(diffs)) / bin_width))
  
  # Mode pulse interval = expected pulse interval. 
  i = np.argmax(hist)
  mode = int(bins[i] + bins[i+1]) / 2

  # Second moment of mode. 
  second_moment = 0
  if mode > 0:
    m = float(mode) / TIMESTAMP_PRECISION
    for j in range(hist.shape[0]-1): 
      x = float(bins[j] + bins[j+1]) / (2 * TIMESTAMP_PRECISION)
      f = float(hist[j]) / hist[i] 
      second_moment += BIN_WIDTH * f * (x - m) ** 2 

  processing_timer_stop = time.time()
  processing_time['expected_pulse_interval'] += processing_timer_stop - processing_timer_start


  return (mode, second_moment)


def parametric_filter(data, tx_params): 
  ''' Parametric filter. Set score to `PARAM_BAD`.

    So far we only look at `band3` and `band10`. 
  '''

  processing_timer_start = time.time()

  (rows, _) = data.shape
  for i in range(rows): 
    if data[i,3] > tx_params['band3'] or data[i,4] > tx_params['band10']:
      data[i,5] = PARAM_BAD

  processing_timer_stop = time.time()
  processing_time['param_filter'] += processing_timer_stop - processing_timer_start


  #return data[data[:,5] != PARAM_BAD]


def burst_filter(data, interval): 
  ''' Burst filter. Set score to `BURST_BAD`.
    
    Remove segments of points whose density exceed the a priori 
    pulse rate by an order of magnitude. For now, it is assumed
    that no transmitter produces more than two pulses a second. 
    Note that we could eventually use the 'pulse_rate' parameter
    in `qraat.tx_parameter`. 
  ''' 

  processing_timer_start = time.time()

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
      # NOTE If it were possible to carry around the row index when
      # computing the histogram, we could mark signals within bad 
      # bins here. 

  # Mark signals within bad bins. 
  (rows, _) = data.shape
  for i in range(rows): 
    for (t0, t1) in bad_intervals:
      if t0 <= data[i,2] and data[i,2] <= t1:
        data[i,5] = BURST_BAD

  processing_timer_stop = time.time()
  processing_time['burst_filter'] += processing_timer_stop - processing_timer_start


  #return data[data[:,5] != BURST_BAD]


def time_filter(data, pulse_interval, pulse_variation, thresh=None):
  ''' Time filter. Calculate absolute score and normalize. 
    
    `thresh` is either None or in [0 .. 1]. If `thresh` is not none,
    it returns data with relative score of at least this value. 
  ''' 

  processing_timer_start = time.time()

  pulse_error = int(SCORE_ERROR(pulse_variation) * TIMESTAMP_PRECISION)
  delta = SCORE_NEIGHBORHOOD * TIMESTAMP_PRECISION / 2 
    
  # Best score theoretically possible for this interval. 
  theoretical_count = SCORE_NEIGHBORHOOD * TIMESTAMP_PRECISION / pulse_interval

  # Put pulses into at most score_neighborhood / pulse_error bins. 
  bins = {}
  for i in range(data.shape[0]):
    if data[i,5] < 0: # Skip if pulse didn't pass a previous filter. 
      continue
  
    t = data[i,2] - (data[i,2] % pulse_error)
    if bins.get(t): 
      bins[t].append(i)
    else: bins[t] = [i]

  # Score pulses in bins with exactly one pulse. 
  for (_, points) in bins.iteritems():
    if len(points) > 1: 
      data[i,5] = 0

    else:
      count = 0
      i = points[0]
      N = (delta / pulse_interval) 
      for n in range(-N+1, N):
        t = data[i,2] + (pulse_interval * n)
        t -= (t % pulse_error)
        if bins.get(t):
          count += 1 
      data[i,5] = count - 1 # Counted myself.
  
  data[:,6] = theoretical_count
  data[:,7] = np.max(data[:,5]) # Max count. 

  processing_timer_stop = time.time()
  processing_time['time_filter'] += processing_timer_stop - processing_timer_start



# TODO Deprecate
def time_filter0(data, pulse_interval, pulse_variation, thresh=None):
  ''' Time filter. Calculate absolute score and normalize. 
    
    `thresh` is either None or in [0 .. 1]. If `thresh` is not none,
    it returns data with relative score of at least this value. 
  ''' 

  pulse_error = int(SCORE_ERROR(pulse_variation) * TIMESTAMP_PRECISION)
  delta = SCORE_NEIGHBORHOOD * TIMESTAMP_PRECISION / 2 
    
  # Best score theoretically possible for this interval. 
  theoretical_count = SCORE_NEIGHBORHOOD * TIMESTAMP_PRECISION / pulse_interval

  # For each pulse, count the number of coroborating points, i.e., 
  # points that are a pulse interval away within paramterized error.
  for i in range(data.shape[0]):
    data[i,6] = theoretical_count
    if data[i,5] < 0: # Skip if pulse didn't pass a previous filter. 
      continue
    
    # Compute neighborhood window. 
    low = data[i,2] - delta
    high = data[i,2] + delta
    neighborhood = data[(low <= data[:,2]) & (data[:,2] <= high)] 
    
    count = 0
    for j in range(neighborhood.shape[0]): 
      offset = abs(data[i,2] - neighborhood[j,2]) % pulse_interval
      if offset <= pulse_error or offset >= pulse_interval - pulse_error:
        count += 1
    
    data[i,5] = count - 1 # Counted myself.
  
  data[:,7] = np.max(data[:,5]) # Max count. 

  #if thresh:
  #  return data[data[:,5].astype(np.float) / data[:,6] > thresh]
  #else:
  #  return data



#### Testing, testing ... #####################################################
if __name__ == '__main__':
  VERBOSE = True 

  def test1(): 
    db_con = util.get_db('writer')
    
    # Calibration data
    #dep_id = 51; site_id = 2; 
    #t_start, t_end = 1376427421, 1376434446
    
    # A walk through the woods 
    #dep_id = 61; site_id = 3; 
    #t_start, t_end = 1396725598, 1396732325
    
    # Fixed tx test data 
    dep_id  = 105
    t_start = 1410721127.0
    t_end   = 1410807696.0

    # A woodrat on Aug 8
    #dep_id = 102; site_id = 2; 
    #t_start, t_end = 1407448817.94, 1407466794.77

    Filter(db_con, dep_id, t_start, t_end)


  def test2():
    db_con = util.get_db('writer')
    for interval in get_score_intervals(1376427421, 1376427421 + 23):
      print interval

 
  test1()
#end main()
