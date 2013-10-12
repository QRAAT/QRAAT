import MySQLdb
import getpass
import numpy as np
import time

mysql_host = "169.237.92.155"
#mysql_host = "10.253.1.55"
mysql_user = "todd"
mysql_db = "qraat"
cal_id=1

start_time_str = "201308131200"#1376420400.0
stop_time_str = "201308131800"#1376442000.0
start_time = time.mktime(time.strptime(start_time_str,'%Y%m%d%H%M%S'))
stop_time = time.mktime(time.strptime(stop_time_str,'%Y%m%d%H%M%S'))

#open database
password = getpass.getpass("Enter password for user: {0} for db: {1} at {2}\nPassword: ".format(mysql_user,mysql_db,mysql_host))
db = MySQLdb.connect(mysql_host, mysql_user, password, mysql_db)
db_cursor = db.cursor()

#get site locations
db_cursor.execute("SELECT ID, easting, northing from sitelist;")
site_data = np.array(db_cursor.fetchall(),dtype=float)

#get steering vector data
sv_siteID = []
sv = []
sv_bearing = []

for j in site_data[:,0]:
  print "Getting Steering Vectors for Site ID #{}".format(j)
  db_cursor.execute("select Bearing, sv1r, sv1i, sv2r, sv2i, sv3r, sv3i, sv4r, sv4i from Steering_Vectors where SiteID=%s and Cal_InfoID=%s", (j, cal_id))
  sv_data = np.array(db_cursor.fetchall(),dtype=float)
  if sv_data.shape[0] > 0:
    sv_siteID.append(j)
    sv_bearing.append(np.array(sv_data[:,0]))
    sv.append(np.array(sv_data[:,1::2]+np.complex(0,1)*sv_data[:,2::2]))

#get pulse groups
print "Getting EST data from {0} to {1}".format(start_time_str, stop_time_str)
db_cursor.execute("select ID, siteid, timestamp, ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i from est where timestamp >= %s and timestamp <= %s;",(start_time, stop_time))
signal_data = np.array(db_cursor.fetchall(),dtype=float)
sig_id = signal_data[:,0]
site_id = signal_data[:,1]
est_time = signal_data[:,2]
signal = signal_data[:,3::2]+np.complex(0,-1)*signal_data[:,4::2]
sort_index = np.argsort(est_time)

if False:
  pulse_groups = []
  group_window = .02
  time_index=0
  while time_index < sort_index.shape[0]:
    t = est_time[sort_index[time_index]]
    temp_pulse = [ sort_index[time_index], ]
    group_index = time_index + 1
    while group_index < sort_index.shape[0] and est_time[sort_index[group_index]] < (t + group_window):
      temp_pulse.append(sort_index[group_index])
      group_index += 1
    time_index = group_index
    pulse_groups.append(temp_pulse)

#get position data
print "Getting Position data"
db_cursor.execute("select estID, easting, northing, bearing from True_Position")
position_data = np.array(db_cursor.fetchall(),dtype=float)


db.close()


likelihoods = np.zeros((len(sort_index),360))
bearings = []
for iter_index in range(len(sort_index)):
  sv_index = sv_siteID.index(site_id[iter_index])
  steering_vectors = sv[sv_index]
  sig = signal[iter_index,np.newaxis,:]
  left_half = np.dot(sig,np.conj(np.transpose(steering_vectors)))
  bearing_likelihood = (left_half*np.conj(left_half)).real
  bearings.append(sv_bearing[sv_index][np.argmax(bearing_likelihood)])
  for index, value in enumerate(sv_bearing[sv_index]):
    likelihoods[iter_index,value] = bearing_likelihood[0,index]

site_pos = np.zeros((site_data.shape[0],),np.complex)
site_pos_id = []
for site_index in range(site_data.shape[0]):
  site_pos[site_index] = np.complex(site_data[site_index,2],site_data[site_index,1])
  site_pos_id.append(site_data[site_index,0])

#center = 4251500+j*574500, step_size = 100
def get_grid(center, step_size, half_span=15):
  position_grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for east_index in range(-half_span,half_span+1):
    for north_index in range(-half_span,half_span+1):
      position_grid[east_index+half_span, north_index+half_span] = center + np.complex(north_index*step_size, east_index*step_size)
  return position_grid

def get_site_bearings(position_grid):
  site_bearings = np.zeros(np.hstack((position_grid.shape,len(sv_siteID))))
  for sv_index, id_index in enumerate(sv_siteID):
    site_bearings[:,:,sv_index] = np.angle(position_grid - site_pos[site_pos_id.index(id_index)])*180/np.pi
  return site_bearings

def get_pos_likelihood(index_list, site_bearings):
  pos_likelihood = np.zeros(site_bearings.shape[0:2])
  for est_index in index_list:
    sv_index = sv_siteID.index(site_id[est_index])
    pos_likelihood += np.interp(site_bearings[:,:,sv_index], range(-360,360), np.hstack((likelihoods[est_index,:], likelihoods[est_index,:])) )
  return pos_likelihood

def position_estimation(index_list):
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

avg_win = 30
pos_est = np.zeros(sort_index.shape, dtype = np.complex)
index=0
while index < sort_index.shape[0]:
  t = est_time[sort_index[index]]
  stop_index = index
  while stop_index < sort_index.shape[0] and est_time[sort_index[stop_index]] - t < avg_win:
    stop_index += 1
  index_list = sort_index[range(index, stop_index)]
  pos_est[sort_index[index]] = position_estimation(index_list)
  index += 1

