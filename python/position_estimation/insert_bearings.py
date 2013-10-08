import MySQLdb
import getpass
import numpy as np
import time

mysql_host = "169.237.92.155"
#mysql_host = "10.253.1.55"
mysql_user = "todd"
mysql_db = "qraat"
cal_id=1
site_id=1
start_time_str = "201308131200"#1376420400.0
stop_time_str = "201308131800"#1376442000.0

#open database
password = getpass.getpass("Enter password for user: {0} for db: {1} at {2}\nPassword: ".format(mysql_user,mysql_db,mysql_host))
db = MySQLdb.connect(mysql_host, mysql_user, password, mysql_db)
db_cursor = db.cursor()

print "Getting Steering Vectors for Site ID #{}".format(site_id)
db_cursor.execute("select Bearing, sv1r, sv1i, sv2r, sv2i, sv3r, sv3i, sv4r, sv4i from Steering_Vectors where SiteID=%s and Cal_InfoID=%s", (site_id, cal_id))

sv_data = np.array(db_cursor.fetchall(),dtype=float)
sv_bearings = sv_data[:,0]
sv = sv_data[:,1::2] + np.complex(0,1)*sv_data[:,2::2]

start_time = time.mktime(time.strptime(start_time_str,'%Y%m%d%H%M%S'))
stop_time = time.mktime(time.strptime(stop_time_str,'%Y%m%d%H%M%S'))

print "Getting est records between {0} and {1} on site ID #{2}".format(start_time, stop_time, site_id)
db_cursor.execute("select ID, ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i from est where siteid=%s and timestamp >= %s and timestamp <= %s;",(site_id, start_time, stop_time))

print "Calculating likelihoods"
signal_data = np.array(db_cursor.fetchall(),dtype=float)
sig_id = signal_data[:,0]
signal = signal_data[:,1::2] + np.complex(0,-1)*signal_data[:,2::2]#conjugate of signal

temp_product = np.dot(signal,np.conjugate(np.transpose(sv)))
likelihood = (temp_product*np.conj(temp_product)).real#est X bearing
maximums = np.argmax(likelihood, axis=1)
bearings = sv_bearings[maximums]

print "Inserting {0} records for {1} bearings: {2} rows".format(likelihood.shape[0],likelihood.shape[1],np.prod(likelihood.shape))
for k in range(likelihood.shape[0]):
  db_cursor.executemany("INSERT INTO azimuth (estID, azimuth, likelihood, Cal_InfoID, maximum) Values (%s, %s, %s, %s, %s);",[ (sig_id[k], sv_bearings[j], likelihood[k,j], cal_id, 1 if (j == maximums[k]) else 0) for j in range(likelihood.shape[1]) ])
