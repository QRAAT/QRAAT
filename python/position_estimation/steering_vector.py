
# Input : data from a callibration run (join on 
#         qraat.True_Position and qraat.est). 
# Output : steering vectors for bearing estimation.
#          (Doesn't actually generate output, just 
#           shows a plot of bearing per time.) 

import qraat
import MySQLdb as mdb
import time, os
import numpy as np
import matplotlib.pyplot as pp


# TODO parameters
avg_span = 5 #size of averaging window, in degrees
cal_id = 1
site_id = 1



# Connect to database.
db_config = qraat.csv('%s/.qraat/db_auth' % os.environ['HOME']).get(view='chris')
db_con    = mdb.connect(db_config.host, 
                        db_config.user,
                        db_config.password,
                        db_config.name)
cur = db_con.cursor()

# get cal data per site from the database. 
cur.execute('''SELECT True_Position.bearing, 
                      est.edsp, 
                      est.ed1r, est.ed1i, est.ed2r, est.ed2i, est.ed3r, est.ed3i, est.ed4r, est.ed4i, 
                      est.frequency, 
                      est.band10, 
                      est.timestamp 
                 FROM True_Position, est 
                WHERE True_Position.estID = est.ID 
                  AND est.siteid=%s 
                  AND True_Position.Cal_InfoID=%s
             ORDER BY est.id DESC 
                LIMIT 1000''' % (site_id, cal_id))

cal_data = np.array(cur.fetchall())
db_con.close()

# calculate pulse values
cal_real_signals = np.array(cal_data[:,2:10],dtype=float)
cal_signals = cal_real_signals[:,::2] + np.complex(0,1) * cal_real_signals[:,1::2]

# generate signals with zero phase on antenna 1
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

# Verify 
sv_bearing = np.zeros((cal_signals.shape[0],))
for j in range(cal_signals.shape[0]):
  temp_signal = np.conj(cal_signals[j,np.newaxis,:])
  temp_sv = np.zeros((bearings.shape[0],))
  for k in range(bearings.shape[0]):
    temp_sv[k] = np.dot(temp_signal, np.dot( np.dot( 
      np.transpose( np.conj( steering_vectors[k,np.newaxis,:] )), 
      steering_vectors[k,np.newaxis,:] ), np.transpose(np.conj(temp_signal)) ))[0,0].real
  sv_bearing[j] = bearings[np.argmax(temp_sv)]

# Insert steering vectors into database. 
cur.executemany('''INSERT INTO Steering_Vectors 
                    (Cal_InfoID, SiteID, Bearing, 
                     sv1r, sv1i, sv2r, sv2i, 
                     sv3r, sv3i, sv4r, sv4i) 
                   VALUES (%s, %s, %s, 
                           %s, %s, %s, %s, 
                           %s, %s, %s, %s)''', 
                           
  [ ( cal_id, site_id, bearings[j], 
      steering_vectors[j,0].real, steering_vectors[j,0].imag,
      steering_vectors[j,1].real, steering_vectors[j,1].imag,
      steering_vectors[j,2].real, steering_vectors[j,2].imag,
      steering_vectors[j,3].real, steering_vectors[j,3].imag ) 
    for j in range(bearings.shape[0]) ]
)

true_bearing = np.array(cal_data[:,0],dtype=float)
true_bearing += 360*(true_bearing < 0)
pp.plot(cal_data[:,12],sv_bearing,'.')
pp.plot(cal_data[:,12],true_bearing,'k.')
pp.xlabel("Timestamp (seconds)")
pp.ylabel("Bearing (Degrees)")
pp.title("Site ID #{} Bearing Estimate".format(site_id))
pp.show()


