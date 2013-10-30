import matplotlib.pyplot as pp
import MySQLdb as mdb
import numpy as np
import time, os, sys
import qraat

# TODO parameters
cal_id=1
start_time_str = "201310140800"
stop_time_str =  "201310141400"
start_time = time.mktime(time.strptime(start_time_str,'%Y%m%d%H%M%S'))
stop_time = time.mktime(time.strptime(stop_time_str,'%Y%m%d%H%M%S'))
#start_time = 1376420400.0 # Cal run
#stop_time =  1376442000.0
# Get database credentials. 
try: 
  db_config = qraat.csv("%s/db_auth" % os.environ['RMG_SERVER_DIR']).get(view='reader')

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
cur = db_con.cursor()

#get site locations
sites = qraat.csv(db_con=db_con, db_table='sitelist')
print sites

#get steering vector data
sv_siteID = []
sv = []
sv_bearing = []

for site in sites:
  print "Getting Steering Vectors for Site ID #{}".format(site.ID)
  cur.execute('''SELECT Bearing, 
                        sv1r, sv1i, sv2r, sv2i, 
                        sv3r, sv3i, sv4r, sv4i 
                   FROM Steering_Vectors 
                  WHERE SiteID=%d and Cal_InfoID=%d''' % (site.ID, cal_id))
  sv_data = np.array(cur.fetchall(),dtype=float)
  if sv_data.shape[0] > 0:
    sv_siteID.append(site.ID)
    sv_bearing.append(np.array(sv_data[:,0]))
    sv.append(np.array(sv_data[:,1::2]+np.complex(0,1)*sv_data[:,2::2]))

print sv_siteID

#get pulse groups
print "Getting EST data from {0} to {1}".format(start_time_str, stop_time_str)
cur.execute('''SELECT ID, siteid, timestamp,
                      ed1r, ed1i, ed2r, ed2i,
                      ed3r, ed3i, ed4r, ed4i
                 FROM est
                WHERE timestamp >= %s 
                  AND timestamp <= %s
                  AND txid = 55
                ORDER BY timestamp ASC''', (start_time, stop_time))
signal_data = np.array(cur.fetchall(), dtype=float)

est_ct = signal_data.shape[0]
if est_ct == 0:
  print >>sys.stderr, "position_est: fatal: no est records for selected time range."
  sys.exit(1)
else: print "position: processing %d records" % est_ct

sig_id =     np.array(signal_data[:,0], dtype=int)
site_id =    np.array(signal_data[:,1], dtype=int)
est_time =   signal_data[:,2]
signal =     signal_data[:,3::2]+np.complex(0,-1)*signal_data[:,4::2]

# Calculate bearing likelihood per est record
likelihoods = np.zeros((est_ct,360))
bearings = []
for iter_index in range(est_ct):
  sv_index = sv_siteID.index(site_id[iter_index])
  # TODO error: no steering_vectors for site_id
  steering_vectors = sv[sv_index]
  sig = signal[iter_index,np.newaxis,:]
  left_half = np.dot(sig, np.conj(np.transpose(steering_vectors)))
  bearing_likelihood = (left_half * np.conj(left_half)).real
  bearings.append( sv_bearing[sv_index][np.argmax(bearing_likelihood)] )
  for index, value in enumerate(sv_bearing[sv_index]):
    likelihoods[iter_index,value] = bearing_likelihood[0,index]

# "Format location of sites"
site_pos = np.zeros((len(sites),),np.complex)
site_pos_id = []
for j in range(len(sites)):
  site_pos[j] = np.complex(sites[j].northing, sites[j].easting)
  site_pos_id.append(sites[j].ID)

# Positions are stored as complex(northing, eassting).

#center = 4251500+j*574500, step_size = 100
def get_grid(center, step_size, half_span=15):
  # Return a 2D array of positions. 
  position_grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for east_index in range(-half_span,half_span+1):
    for north_index in range(-half_span,half_span+1):
      position_grid[east_index+half_span, north_index+half_span] = center + np.complex(north_index*step_size, east_index*step_size)
  return position_grid

def get_site_bearings(position_grid):
  # Return a 3D array of bearings (in degree) over the position 
  # grid, with the 3rd dimension is over different sites
  site_bearings = np.zeros(np.hstack((position_grid.shape,len(sv_siteID))))
  for sv_index, id_index in enumerate(sv_siteID):
    site_bearings[:,:,sv_index] = np.angle(position_grid - site_pos[site_pos_id.index(id_index)])*180/np.pi
  return site_bearings

def get_pos_likelihood(index_list, site_bearings):
  # Return a 2D array of likelihoods
  pos_likelihood = np.zeros(site_bearings.shape[0:2])
  for est_index in index_list:
    sv_index = sv_siteID.index(site_id[est_index])
    pos_likelihood += np.interp(site_bearings[:,:,sv_index], range(-360,360), np.hstack((likelihoods[est_index,:], likelihoods[est_index,:])) )
  return pos_likelihood

def position_estimation(index_list):
  # Iteratively finds the position of maximum likelihood
  grid_center = np.complex(4260500,574500)
  step_size = 100
  count = 0
  while count < 3:
    position_grid = get_grid(grid_center,step_size)
    site_bearings = get_site_bearings(position_grid)
    sum_likelihood = get_pos_likelihood(index_list, site_bearings)
    grid_center = position_grid.flat[np.argmax(sum_likelihood)]
    step_size = step_size / 10
    count += 1
  return grid_center

# Calculate position estimate in a 30 second window ahead 
# of each est. Store in 1D array indexed by time. 
avg_win = 30
pos_est = np.zeros(est_ct, dtype = np.complex)
index=0
while index < est_ct:
  t = est_time[index]
  stop_index = index
  while stop_index < est_ct and est_time[stop_index] - t < avg_win:
    stop_index += 1
  index_list = range(index, stop_index)
  pos_est[index] = position_estimation(index_list)
  index += 1

print pos_est

pp.plot(
 [s.easting for s in sites], 
 [s.northing for s in sites], 'ro')

pp.plot( 
 np.imag(pos_est), 
 np.real(pos_est), '.', alpha=0.3)

pp.show()
