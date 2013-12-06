import MySQLdb as mdb
import numpy as np
import time, os, sys
import qraat.csv


# Get database credentials. 
def get_db():
  try: 
    db_config = qraat.csv("%s/db_auth" % os.environ['RMG_SERVER_DIR']).get(view='writer')

  except KeyError: 
    print >>sys.stderr, "position: error: undefined environment variables. Try `source rmg_env.`" 
    sys.exit(1) 

  except IOError, e: 
    print >>sys.stderr, "position: error: missing DB credential file '%s'." % e.filename
    sys.exit(1)

  # Connect to the database. 
  db_con = mdb.connect(db_config.host, 
                       db_config.user,
                       db_config.password,
                       db_config.name)
  return db_con

def get_site_data(db_con, cal_id):
  print "position: fetching site and cal data"

  # Get site locations.
  sites = qraat.csv(db_con=db_con, db_table='sitelist')

  # Get steering vector data.
  steering_vectors = {} # site.ID -> sv
  bearings = {}         # site.ID -> bearing
  to_be_removed = []
  cur = db_con.cursor()
  for site in sites:
    cur.execute('''SELECT Bearing, 
                          sv1r, sv1i, sv2r, sv2i, 
                          sv3r, sv3i, sv4r, sv4i 
                     FROM Steering_Vectors 
                    WHERE SiteID=%d and Cal_InfoID=%d''' % (site.ID, cal_id))
    sv_data = np.array(cur.fetchall(),dtype=float)
    if sv_data.shape[0] > 0:
      steering_vectors[site.ID] = np.array(sv_data[:,1::2] + np.complex(0,1) * sv_data[:,2::2])
      bearings[site.ID] = np.array(sv_data[:,0])
    else:
      to_be_removed.append(site)
  while len(to_be_removed) > 0:
    sites.table.remove(to_be_removed.pop())

  # Format site locations as np.complex's. 
  for site in sites:
    setattr(site, 'pos', np.complex(sites[j].northing, sites[j].easting))

  return (sites, bearings, steering_vectors)

def get_est_data(cur, t_start, t_end, tx_id):
  print "position: fetching pulses for transmitter and time range"

  # Get pulses in time range.  
  cur.execute('''SELECT ID, siteid, timestamp,
                        ed1r, ed1i, ed2r, ed2i,
                        ed3r, ed3i, ed4r, ed4i
                   FROM est
                  WHERE timestamp >= %s
                    AND timestamp <= %s
                    AND txid = %s
                  ORDER BY timestamp ASC''', (t_start, 
                                              t_end, 
                                              tx_id))

  signal_data = np.array(cur.fetchall(), dtype=float)
  est_ct = signal_data.shape[0]
  if est_ct == 0:
    print >>sys.stderr, "position: fatal: no est records for selected time range."
    sys.exit(1)
  else: print "position: processing %d records" % est_ct

  sig_id =   np.array(signal_data[:,0], dtype=int)
  site_id =  np.array(signal_data[:,1], dtype=int)
  est_time = signal_data[:,2]
  signal =   signal_data[:,3::2]+np.complex(0,-1)*signal_data[:,4::2]
  return (sig_id, site_id, est_time, signal)

# Calculate the likelihood of each bearing for each pulse. 
def calc_likelihoods(signal, site_id, bearings, steering_vectors):
  print "position: calculating pulse bearing likelihoods"

  likelihoods = np.zeros((est_ct,360))
  for i in range(signal.shape[0]):
    try: 
      sv =  steering_vectors[site_id[i]]
    except KeyError:
      print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % site_id[i]
      sys.exit(1)

    sig = signal[i,np.newaxis,:]
    left_half = np.dot(sig, np.conj(np.transpose(sv)))
    bearing_likelihood = (left_half * np.conj(left_half)).real
    for j, value in enumerate(bearings[site_id[i]]):
      likelihoods[i, value] = bearing_likelihood[0, j]
  return likelihoods



def position_estimation(index_list, center, scale, sites, likelihoods, half_span=15):
  ''' Estimate the position of a transmitter over time interval ``[i, j]``.

    Generate a set of candidate points centered around ``center``. 
    Calculate the bearing to the receiver sites from each of this points. 
    The log likelihood of a candidate corresponding to the actual location
    of the target transmitter over the time window is equal to the sum of
    the likelihoods of each of these bearings given the signal characteristics
    of the ESTs in the window. 
  '''
  
  #: Generate candidate points centered around ``center``. 
  grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for e in range(-half_span,half_span+1):
    for n in range(-half_span,half_span+1):
      grid[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)

  #: The third dimension of the search space: bearings from each 
  #: candidate point to each receiver site. 
  #site_bearings = np.zeros(np.hstack((grid.shape,len(sites))))
  site_bearings = {}
  for site in sites:
    #site_bearings[:,:,sv_index] = np.angle(grid - site.pos) * 180 / np.pi
    site_bearings[site.id] = np.angle(grid - site.pos) * 180 / np.pi

  #: Based on bearing likelihoods for EST's in time range, calculate
  #: the log likelihood of each candidate point. 
  pos_likelihood = np.zeros(site_bearings.shape[0:2])
  for est_index in index_list: 
    sv_index = site_id[est_index]
    try:
      pos_likelihood += np.interp(site_bearings[sv_index], 
                                range(-360, 360), 
                                np.hstack((likelihoods[est_index,:], 
                                likelihoods[est_index,:])) )
    except KeyError:
      pass

  return grid.flat[np.argmax(pos_likelihood)]

def calc_positions(cal_id, tx_id, t_start, t_end, t_delta, t_window, verbose = False):
  con = get_db()
  (sites, bearings, steering_vectors) = get_site_data(con, cal_id)
  cur = con.cursor()
  (sig_id, site_id, est_time, signal) = get_est_data(cur, t_start, t_end, tx_id)
  likelihoods = calc_likelihoods(signal, site_id, bearings, steering_vectors)
  pos_est = estimate_positions(est_time, t_window, t_delta, sites, likelihoods)
  insert_positions(cur, pos_est, tx_id)
  return pos_est, sites

def estimate_positions(est_time, t_window, t_delta, sites, likelihoods):
  #: Calculated positions (time, pos). 
  pos_est = [] 
  est_ct = likelihoods.shape[0]
  #: The time step (in seconds) for the position estimation
  #: calculation.
  #t_delta = options.t_delta

  #: Time averaging window (in seconds). 
  #t_window = options.t_window

  #: Center of Quail Ridge reserve (northing, easting). This is the first
  #: "candidate point" used to construct the search space grid. 
  center = np.complex(4260500, 574500) 

  print "position: calculating position"
  if verbose:
    print "%15s %-19s %-19s %-19s" % ('time window', 
                '100 meters', '10 meters', '1 meter')

  i = 0

  try: 
    while i < est_ct - 1:

      # Find the index j corresponding to the end of the time window. 
      j = i + 1
      while j < est_ct - 1 and (est_time[j + 1] - est_time[i]) <= t_window: 
        j += 1

      if verbose: 
        print "%7d %7d" % (i, j), 
      
      scale = 100
      pos = center
      while scale >= 1: # 100, 10, 1 meters ...  
        pos = position_estimation(range(i,j), pos, scale, sites, likelihoods)
        if verbose:
          print "%8dn,%de" % (pos.real, pos.imag),
        scale /= 10
      pos_est.append(((est_time[i] + est_time[j]) / 2, 
                      pos.imag,  # easting 
                      pos.real)) # northing

      if verbose: print

      # Step index i forward t_delta seconds. 
      j = i + 1
      while i < est_ct - 1 and (est_time[i + 1] - est_time[j]) <= t_delta: 
        i += 1

  except KeyboardInterrupt: pass

  return pos_est

def insert_positions(cur, pos_est, tx_id):

    # Insert results into database. 
    cur.executemany('''INSERT INTO Position 
                        (txid, timestamp, easting, northing)
                       VALUES (%s, %s, %s, %s)''', [(tx_id, pe[0], pe[1], pe[2]) for pe in pos_est])

