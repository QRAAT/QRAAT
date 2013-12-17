import MySQLdb as mdb
import numpy as np
import time, os, sys
import qraat.csv

from qraat.util import get_field, remove_field

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

  deps = []

  # Get site locations.
  sites = qraat.csv(db_con=db_con, db_table='sitelist')

  sv_deps_by_site = {}

  for row in sites:
    deps.append(('sitelist', row.ID))

  # Get steering vector data.
  steering_vectors = {} # site.ID -> sv
  bearings = {}         # site.ID -> bearing
  to_be_removed = []
  cur = db_con.cursor()
  for site in sites:
    cur.execute('''SELECT ID, Bearing,
                          sv1r, sv1i, sv2r, sv2i,
                          sv3r, sv3i, sv4r, sv4i
                     FROM Steering_Vectors
                    WHERE SiteID=%d and Cal_InfoID=%d''' % (site.ID, cal_id))
    raw_data = cur.fetchall()
    prov_sv_ids = get_field(raw_data, 0)
    data_no_ids = remove_field(raw_data, 0)
    sv_data = np.array(data_no_ids,dtype=float)
    if sv_data.shape[0] > 0:
      steering_vectors[site.ID] = np.array(sv_data[:,1::2] + np.complex(0,1) * sv_data[:,2::2])
      sv_deps_by_site[site.ID] = prov_sv_ids
      bearings[site.ID] = np.array(sv_data[:,0])
    else:
      to_be_removed.append(site)
  while len(to_be_removed) > 0:
    sites.table.remove(to_be_removed.pop())

  # Format site locations as np.complex's.
  for site in sites:
    setattr(site, 'pos', np.complex(site.northing, site.easting))

  return (sites, bearings, steering_vectors, prov_sv_ids, deps, sv_deps_by_site)

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

  raw_data = cur.fetchall()
  prov_est_ids = get_field(raw_data, 0)
  signal_data = np.array(raw_data, dtype=float)
  est_ct = signal_data.shape[0]
  if est_ct == 0:
    print >>sys.stderr, "position: fatal: no est records for selected time range."
    sys.exit(1)
  else: print "position: processing %d records" % est_ct

  sig_id =   np.array(signal_data[:,0], dtype=int)
  site_id =  np.array(signal_data[:,1], dtype=int)
  est_time = signal_data[:,2]
  signal =   signal_data[:,3::2]+np.complex(0,-1)*signal_data[:,4::2]
  return (sig_id, site_id, est_time, signal, prov_est_ids)

# Calculate the likelihood of each bearing for each pulse.
def calc_likelihoods(signal, site_id, bearings, steering_vectors, sv_ids, est_ids, sv_deps_by_site):

  record_provenance_from_site_data = False

  print "position: calculating pulse bearing likelihoods"

  likelihoods = np.zeros((signal.shape[0],360))
  for i in range(signal.shape[0]):
    try:
      sv =  steering_vectors[site_id[i]]
      sv_deps = sv_deps_by_site[site_id[i]]
    except KeyError:
      print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % site_id[i]
      sys.exit(1)

    sig = signal[i,np.newaxis,:]
    sig_dep = est_ids[i]
    left_half = np.dot(sig, np.conj(np.transpose(sv)))
    bearing_likelihood = (left_half * np.conj(left_half)).real
    bearing_likelihood_deps = [('Steering_Vectors', x) for x in sv_deps]
    bearing_likelihood_deps.append(('est', sig_dep))

    likelihood_deps = {}
    for j, value in enumerate(bearings[site_id[i]]):
      likelihoods[i, value] = bearing_likelihood[0, j]
      likelihood_deps[i, value] = bearing_likelihood_deps

  if record_provenance_from_site_data:
    return likelihoods, likelihood_deps
  else:
    return likelihoods, []



def position_estimation(index_list, center, scale, sites, likelihoods, likelihood_deps, site_id, half_span=15):
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
    site_bearings[site.ID] = np.angle(grid - site.pos) * 180 / np.pi

  #: Based on bearing likelihoods for EST's in time range, calculate
  #: the log likelihood of each candidate point.
  pos_likelihood = np.zeros(site_bearings[sites[0].ID].shape[0:2])
  for est_index in index_list:
    sv_index = site_id[est_index]
    try:
      pos_likelihood += np.interp(site_bearings[sv_index],
                                range(-360, 360),
                                np.hstack((likelihoods[est_index,:],
                                likelihoods[est_index,:])) )
      # SEAN: Would use likelihood_deps right here if I was using them
    except KeyError:
      pass

  return grid.flat[np.argmax(pos_likelihood)]

def calc_positions(cal_id, tx_id, t_start, t_end, t_delta, t_window, verbose = False):
  con = get_db()

  cur = con.cursor()
  (sites, bearings, steering_vectors, sv_ids, sitelist_deps, sv_deps_by_site) = get_site_data(con, cal_id)
  cur = con.cursor()
  (sig_id, site_id, est_time, signal, est_ids) = get_est_data(cur, t_start, t_end, tx_id)
  likelihoods, likelihood_deps = calc_likelihoods(signal, site_id, bearings, steering_vectors, sv_ids, est_ids, sv_deps_by_site)
  pos_est, pos_est_deps = estimate_positions(est_time, t_window, t_delta, sites, likelihoods, likelihood_deps, site_id, est_ids, verbose)
  insert_positions(cur, pos_est, pos_est_deps, tx_id)
  return pos_est, sites

def estimate_positions(est_time, t_window, t_delta, sites, likelihoods, likelihood_deps, site_id, est_ids, verbose=False):
  #: Calculated positions (time, pos).
  pos_est = []
  pos_est_deps = []
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
  start_step = np.ceil(est_time[0] / t_delta)
  while start_step*t_delta - (t_window / 2.0) < est_time[0]:
    start_step += 1
  start_step -= 1

  end_step = np.floor(est_time[-1] / t_delta)
  while end_step*t_delta + (t_window / 2.0) > est_time[-1]:
    end_step -= 1
  end_step += 1


  try:
    for time_step in range(int(start_step),int(end_step)):

      # Find the indexes corresponding to the time window.
      est_index_list = np.where(np.abs(est_time - time_step*t_delta - t_window / 2.0) <= t_window / 2.0)[0]#where returns a tuple for some reason

      if len(est_index_list) > 0 and len(set(site_id[est_index_list])) > 1:
        if verbose: print "Time window {0} - {1}".format(time_step*t_delta - t_window / 2.0, time_step*t_delta + t_window)
        scale = 100
        pos = center
        while scale >= 1: # 100, 10, 1 meters ...
          pos = position_estimation(est_index_list, pos, scale, sites, likelihoods, likelihood_deps, site_id)
          if verbose:
            print "%8dn,%de" % (pos.real, pos.imag),
          scale /= 10
        pos_deps = []
        # Determine components of est that contribute to the computed position.
        for est_index in est_index_list:
          pos_deps.append(est_ids[est_index])
        pos_est.append((time_step*t_delta,
                        pos.imag,  # easting
                        pos.real)) # northing

        pos_est_deps.append({'est':tuple(pos_deps)})
        if verbose: print

  except KeyboardInterrupt: pass

  return pos_est, pos_est_deps

def insert_positions(cur, pos_est, pos_est_deps, tx_id):

    insert_statement = '''INSERT INTO Position
                        (txid, timestamp, easting, northing)
                       VALUES (%s, %s, %s, %s)'''
    # Insert results into database.
    #cur.executemany(, [(tx_id, pe[0], pe[1], pe[2]) for pe in pos_est])

    all_insertions = []
    for pos_est_index in range(len(pos_est)):
      this_pos_est = pos_est[pos_est_index]
      this_pos_est_deps = pos_est_deps[pos_est_index]
      cur.execute(insert_statement, (tx_id, this_pos_est[0], this_pos_est[1], this_pos_est[2]))
      pos_est_insertion_id = cur.lastrowid
      all_insertions.append(pos_est_insertion_id)
      handle_provenance_insertion(cur, this_pos_est_deps, {'Position':(pos_est_insertion_id,)})

def compress(s):

  strings = []
  ss = sorted(s, reverse=True)

  last_num = None
  sequence_start = None

  while len(ss) != 0:
    i = ss.pop()
    if last_num is None:
      # the start
      sequence_start = i
    elif last_num + 1 == i:
      # still in sequence
      pass
    else:
      # sequence over
      if sequence_start == last_num:
        strings.append(str(sequence_start))
      else:
        strings.append('%d-%d' % (sequence_start, last_num))
      sequence_start = i
    last_num = i

  # add last
  if sequence_start == last_num:
    strings.append(str(sequence_start))
  else:
    strings.append('%d-%d' % (sequence_start, last_num))


  return ','.join(strings)

def handle_provenance_insertion(cur, depends_on, obj):
  query = 'insert into provenance (obj_table, obj_id, dep_table, dep_id) values (%s, %s, %s, %s);'
  prov_args = []
  for dep_k in depends_on.keys():
    for dep_v in depends_on[dep_k]:
      for obj_k in obj.keys():
        for obj_v in obj[obj_k]:
          args = (obj_k, obj_v, dep_k, dep_v)
          prov_args.append(args)
  cur.executemany(query, prov_args)

