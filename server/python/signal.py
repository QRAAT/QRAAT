# Time filter. This program attempts to remove false positives from 
# the pulse data based on the rate at which the transmitter emits 
# pulses. Neighboring points are used to coraborate the validity of
# a given point. This is on a per transmitter per site basis; a 
# useful extension to this work will be to coroborate points between
# sites. 

# TODO Record pulse interval for score window in DB.  

# TODO Account for the percentage of time the system is listening
#      for the transmitter. 

# TODO Don't double count pulses that fall within the same error 
#      window. To do this, throw pulses in a bucket data structure. 


# NOTE It would be nice if np.where() would return a shallow
#      copy. Then we could do 
#       time_filter(burst_filter(parametric_filter(data, _), _), _)

# NOTE The larger the score window, the more accurate we calculate 
#      the expected pulse interval.


import sys
import qraat
import numpy as np
import MySQLdb as mdb

#### Constants and parameters for per site/transmitter pulse filtering. #######

# Some parameters. 
BURST_INTERVAL = 10         # seconds
BURST_THRESHOLD = 20        # pulses/second
SCORE_INTERVAL = 60 * 15    # seconds 
SCORE_NEIGHBORHOOD = 60 * 3 # seconds (must divide `SCORE_INTERVAL` evenly)
SCORE_ERROR = 0.02          # seconds

# Log output. 
VERBOSE = False

# Factor by which to multiply timestamps. 
TIMESTAMP_PRECISION = 1000

# Some constants. 
PARAM_BAD = -1
BURST_BAD = -2 



#### High level call. #########################################################

def debug_output(msg): 
  if VERBOSE: 
    print "signal: %s" % msg


def Filter(db_con, dep_id, site_id, t_start, t_end): 
  ''' Score points per site and transmitter, insert into database. 
  
    Return the number of pulses that were scored and the last id
    processed into the database.  
  '''   

  total = 0; max_id = 0
  tx_params = get_tx_params(db_con, dep_id)
  debug_output("depID=%d parameters: band3=%s, band10=%s" 
     % (dep_id, 'nil' if tx_params['band3'] == sys.maxint else tx_params['band3'],
                'nil' if tx_params['band10'] == sys.maxint else tx_params['band10']))
          
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

    # Tbe only way to coroborate isolated points is with other sites. 
    if data[data.shape[0]-1,2] - data[0,2] > 0: 
      burst_filter(data, augmented_interval)
      time_filter(data)
    
    # When inserting, exclude overlapping points.
    (count, id) = insert_data(db_con, 
       data[(data[:,2] >= (interval[0] * TIMESTAMP_PRECISION)) & 
            (data[:,2] <= (interval[1] * TIMESTAMP_PRECISION))])

    total += count
    max_id = id if max_id < id else max_id
  
  return (total, max_id)



#### Handle pulse data. ####################################################### 

def get_score_intervals(t_start, t_end): 
  ''' Return a list of scoring windows given arbitrary start and finish. '''  
 
  t_start = int(t_start); t_end = int(t_end)
  intervals = range(t_start - (t_start % SCORE_INTERVAL), 
                    t_end + (t_end % SCORE_INTERVAL),
                    SCORE_INTERVAL)
                    
  for i in range(1,len(intervals)): 
    yield (intervals[i-1], intervals[i])


def get_interval_data(db_con, dep_id, site_id, interval):
  ''' Get pulse data for interval. 
  
    Last columns are for the score and theoretically best score of the
    record. (X[:,5], X[:,6] resp.) Initially, there values are 0. 
  ''' 

  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, band3, band10, 0, 0, 0  
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


def insert_data(db_con, data): 
  ''' Insert scored data, updating existng records. 
  
    Return the number of inserted scores and the maximum estID. 
  ''' 
  
  (row, _) = data.shape; 
  inserts = []; deletes = []
  for i in range(row):
    inserts.append((data[i,0], data[i,5], data[i,6], data[i,7]))
    deletes.append(data[i,0])

  # TODO Insert or update. 
  cur = db_con.cursor()
  cur.executemany('DELETE FROM estscore WHERE estID = %s', deletes)
  cur.executemany('''INSERT INTO estscore (estID, score, theoretical_score, max_score) 
                            VALUES (%s, %s, %s, %s)''', inserts)

  max_id = np.max(data[:,0]) if len(inserts) > 0 else 0
  return (len(inserts), max_id)


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



##### Per site/transmitter filters. ###########################################

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
  #                                             / (2 * TIMESTAMP_PRECISION))
  return int(bins[i] + bins[i+1]) / 2


def parametric_filter(data, tx_params): 
  ''' Parametric filter. Set score to `PARAM_BAD`.

    So far we only look at `band3` and `band10`. 
  '''

  (rows, _) = data.shape
  for i in range(rows): 
    if data[i,3] > tx_params['band3'] or data[i,4] > tx_params['band10']:
      data[i,5] = PARAM_BAD

  return data[data[:,5] != PARAM_BAD]


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
      # NOTE If it were possible to carry around the row index when
      # computing the histogram, we could mark signals within bad 
      # bins here. 

  # Mark signals within bad bins. 
  (rows, _) = data.shape
  for i in range(rows): 
    for (t0, t1) in bad_intervals:
      if t0 <= data[i,2] and data[i,2] <= t1:
        data[i,5] = BURST_BAD

  return data[data[:,5] != BURST_BAD]


def time_filter(data, thresh=None):
  ''' Time filter. Calculate absolute score and normalize. 
    
    `thresh` is either None or in [0 .. 1]. If `thresh` is not none,
    it returns data with relative score of at least this value. 
  ''' 

  # Compute expected pulse interval. 
  pulse_interval = expected_pulse_interval(data)
  pulse_error = int(SCORE_ERROR * TIMESTAMP_PRECISION)
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

  if thresh:
    return data[data[:,5].astype(np.float) / data[:,6] > thresh]
  else:
    return data



#### Testing, testing ... #####################################################

def test1(): 
  db_con = qraat.util.get_db('writer')
  
  # Calibration data
  #dep_id = 51; site_id = 2; 
  #t_start, t_end = 1376427421, 1376434446
  
  # A walk through the woods 
  #dep_id = 61; site_id = 3; 
  #t_start, t_end = 1396725598, 1396732325
  
  # A woodrat on Aug 8
  dep_id = 102; site_id = 2; 
  t_start, t_end = 1407448817.94, 1407466794.77

  tx_params = get_tx_params(db_con, dep_id)
  count = 0
  p = 0 

  for interval in get_score_intervals(t_start, t_end):
    data = get_interval_data(db_con, dep_id, site_id, interval)
    if data.shape[0] == 0: 
      print "skipping empty chunk."
      continue
    
    parametric_filter(data, tx_params)

    if data.shape[0] > 1 and data[data.shape[0]-1,2] - data[0,2] > 0: 
      burst_filter(data, interval)
      filtered_data = time_filter(data, 0.15)

      #insert_data(db_con, data)

      # Output ... 
        
      if True: 
        print "Time:", interval, "Count:", data.shape[0]
        print data.shape, filtered_data.shape
        fella = filtered_data
        if fella.shape[0] > 0 and fella[fella.shape[0]-1,2] - fella[0,2] > 0: 
          max_score = float(np.max(fella[:,5]))
          for i in range(fella.shape[0]):
            row = fella[i,:]
            theoretical_score = float(row[6])
            relscore = round(row[5] / theoretical_score, 3)
            q = round(row[2] / 1000.0, 2)
            print row[0], q, row[5], row[6], relscore, round(q-p, 2)
            p = q
          print 

    else: print "too small."

def test2():
  db_con = qraat.util.get_db('writer')
  for interval in get_score_intervals(1376427421, 1376427421 + 23):
    print interval

if __name__ == '__main__': 
  test1()
