import rmg.estimation.gps_data as gps_data
import MySQLdb
import getpass
import time
import numpy as np
import matplotlib.pyplot as pp

avg_span = 5 #size of averaging window, in degrees
cal_id = 1
site_id = 1
mysql_host = "169.237.92.155"
#mysql_host = "10.253.1.55"
mysql_user = "todd"
mysql_db = "qraat"

#open database
password = getpass.getpass("Enter password for user: {0} for db: {1} at {2}\nPassword: ".format(mysql_user,mysql_db,mysql_host))


db = MySQLdb.connect(mysql_host, mysql_user, password, mysql_db)
db_cursor = db.cursor()

#  get cal data per site
db_cursor.execute("select True_Position.bearing, est.edsp, est.ed1r, est.ed1i, est.ed2r, est.ed2i, est.ed3r, est.ed3i, est.ed4r, est.ed4i, est.frequency, est.band10, est.timestamp from True_Position, est where True_Position.estID=est.ID AND est.siteid=%s AND True_Position.Cal_InfoID=%s;",(site_id, cal_id))

cal_data = np.array(db_cursor.fetchall())
db.close()

#  calculate pulse values
cal_real_signals = np.array(cal_data[:,2:10],dtype=float)
cal_signals = cal_real_signals[:,::2] + np.complex(0,1) * cal_real_signals[:,1::2]


#  generate signals with zero phase on antenna 1
cal_spherical_signals = np.zeros(cal_real_signals.shape)
cal_spherical_signals[:,0] = np.arctan2(cal_real_signals[:,1], cal_real_signals[:,0])
cal_phase0_signals = np.exp(np.complex(0,-1)*np.dot(np.angle(cal_signals[:,0:1]),np.ones((1,4)))) * cal_signals

# average signal over bearing
steering_vectors = np.zeros((0,4), np.complex)
bearings = np.zeros((0,))
for j in range(360):
  temp_bearings = (cal_data[:,0] - j + avg_span/2 + 360*5) % 360
  temp_mask = temp_bearings < avg_span
  if np.sum(temp_mask) > 0:
    bearings = np.hstack((bearings, [j,]))
    temp_matrix = np.dot(np.transpose(np.conj(cal_phase0_signals[temp_mask, :])),cal_phase0_signals[temp_mask, :])
    (w,v) = np.linalg.eigh(temp_matrix)
    steering_vectors = np.vstack((steering_vectors, v[np.newaxis,:,np.argmax(w)]))

with open("ID{}_pat.csv".format(site_id),'w') as patcsv:
  for j in range(bearings.shape[0]):
    patcsv.write("{0:f}".format(bearings[j]))
    for k in range(steering_vectors.shape[1]):
      patcsv.write(", {0:f}, {1:f}".format(steering_vectors[j,k].real, steering_vectors[j,k].imag))
    patcsv.write("\n")

sv_bearing = np.zeros((cal_signals.shape[0],))
for j in range(cal_signals.shape[0]):
  temp_signal = np.conj(cal_signals[j,np.newaxis,:])
  temp_sv = np.zeros((bearings.shape[0],))
  for k in range(bearings.shape[0]):
    temp_sv[k] = np.dot(temp_signal, np.dot( np.dot( np.transpose(np.conj(steering_vectors[k,np.newaxis,:])), steering_vectors[k,np.newaxis,:] ), np.transpose(np.conj(temp_signal)) ) )[0,0].real
  
  sv_bearing[j] = bearings[np.argmax(temp_sv)]

true_bearing = np.array(cal_data[:,0],dtype=float)
true_bearing += 360*(true_bearing < 0)
pp.plot(cal_data[:,12],sv_bearing,'.')
pp.plot(cal_data[:,12],true_bearing,'k.')
pp.xlabel("Timestamp (seconds)")
pp.ylabel("Bearing (Degrees)")
pp.title("Site ID #{} Bearing Estimate".format(site_id))
pp.show()


