import gps_data
import MySQLdb
import getpass
import time
import numpy as np


gpx_track_filename='/home/todd/GPX_20130813/Current/Current.gpx'
hemisphere_initial="N"
mysql_host = "169.237.92.155"
#mysql_host = "10.253.1.55"
mysql_user = "todd"
mysql_db = "qraat"
start_time_str = "201308131200"#1376420400.0
stop_time_str = "201308131800"#1376442000.0
#bandwidth = 1000
cal_id="1"

#import gpx data - get time, easting, northing
gps = gps_data.gps_data(gpx_track_filename)

#open database
password = getpass.getpass("Enter password for user: {0} for db: {1} at {2}\nPassword: ".format(mysql_user,mysql_db,mysql_host))
db = MySQLdb.connect(mysql_host, mysql_user, password, mysql_db)
db_cursor = db.cursor()

#insert gps data into database
db_cursor.executemany("INSERT INTO GPS_Calibration_Data (Cal_InfoID, timestamp, latitude, longitutde, elevation, easting, northing, zone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ;", [ (cal_id, gps.time[j], gps.latitude[j], gps.longitude[j], gps.elevation[j], gps.easting[j], gps.northing[j], "{0:.0f}{1}".format(gps.zone[j], hemisphere_initial)) for j in range(gps.num_records) ])

#build temporary table of cal data
#db_cursor.execute("CREATE TEMPORARY TABLE temp_cal_est LIKE est;")
start_time = time.mktime(time.strptime(start_time_str,'%Y%m%d%H%M%S'))
stop_time = time.mktime(time.strptime(stop_time_str,'%Y%m%d%H%M%S'))
#db_cursor.execute("INSERT temp_cal_est SELECT * from est WHERE timestamp >= {0} AND timestamp <= {1};".format(start_time,stop_time))

#get site data of cal'ed sites
print "Getting site list"
#db_cursor.execute("select distinct(est.siteid), sitelist.easting, sitelist.northing, sitelist.name from est join sitelist on sitelist.ID=est.siteid and est.timestamp >= {0} and est.timestamp <= {1};".format(start_time, stop_time))
db_cursor.execute("select ID, easting, northing, name from sitelist;")
site_data = np.array(db_cursor.fetchall())

#Per Site:
for site_iter in range(len(site_data)):

#  import good pulse data from site - bw10<1000 - time, fdsp, fd*[r,i]
  print "Getting data from {}".format(site_data[site_iter,3])
  db_cursor.execute("select timestamp, ID from est where siteid=%s and timestamp >= %s and timestamp <= %s;",(site_data[site_iter,0], start_time, stop_time))
  est_data=np.array(db_cursor.fetchall())
  num_records = est_data.shape[0]
  print "Found {} records".format(num_records)

  if num_records > 0:
#  calculate pulse position from time, linear interpolation
    print "Calculating"
    est_time = np.array(est_data[:,0],dtype=float)
    est_easting = np.interp(est_time,gps.time,gps.easting)
    est_northing = np.interp(est_time,gps.time,gps.northing)

#  calculate pulse bearing
    est_bearing = np.arctan2(est_easting-float(site_data[site_iter,1]),est_northing-float(site_data[site_iter,2]))*180/np.pi

    print "Inserting"
    db_cursor.executemany("INSERT INTO True_Position (estID, Cal_InfoID, easting, northing, bearing) VALUES (%s, %s, %s, %s, %s) ;",[ (est_data[j,1], cal_id, est_easting[j], est_northing[j], est_bearing[j]) for j in range(num_records) ])


