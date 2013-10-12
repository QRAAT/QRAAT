
# Input : GPS data per time, est's from calibration run
# Output : qraat.True_Position 
# Uses gps_data.py. Interpolate GPS with est records from cal run


import qraat
import time, os
import numpy as np
import MySQLdb as mdb


# TODO parameters
gpx_track_filename='/home/todd/GPX_20130813/Current/Current.gpx'
hemisphere_initial="N"
start_time_str = "201308131200"#1376420400.0
stop_time_str = "201308131800"#1376442000.0
#bandwidth = 1000
cal_id="1"

start_time = time.mktime(time.strptime(start_time_str,'%Y%m%d%H%M%S'))
stop_time = time.mktime(time.strptime(stop_time_str,'%Y%m%d%H%M%S'))



# Connect to database. 
db_config = qraat.csv('%s/.qraat/db_auth' % os.environ['HOME']).get(view='chris')
db_con    = mdb.connect(db_config.host, 
                        db_config.user,
                        db_config.password,
                        db_config.name)
cur = db_con.cursor()

# Import gpx data - get time, easting, northing
gps = qraat.gps(gpx_track_filename)

# Insert gps data into database. 
cur.executemany('''INSERT INTO GPS_Calibration_Data 
                              (Cal_InfoID, timestamp, latitude, 
                               longitutde, elevation, 
                               easting, northing, zone) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ;''', 
  [ ( cal_id, gps.time[j], gps.latitude[j], 
      gps.longitude[j], gps.elevation[j], 
      gps.easting[j], gps.northing[j], 
      "{0:.0f}{1}".format(gps.zone[j], hemisphere_initial) ) 
    for j in range(gps.num_records) ]
)

for site in qraat.csv(db_con=db_con, db_table='sitelist'):

  # import good pulse data from site - bw10<1000 - time, fdsp, fd*[r,i]
  print "Getting data from {}".format(site.name)
  cur.execute('''SELECT timestamp, ID 
                   FROM est 
                  WHERE siteid=%s 
                    AND timestamp >= %s 
                    AND timestamp <= %s''',(site.ID, start_time, stop_time))

  est_data = np.array(cur.fetchall())
  num_records = est_data.shape[0]
  print "Found {} records".format(num_records)

  if num_records > 0:
  
    # calculate pulse position from time, linear interpolation 
    print "Calculating"
    est_time = np.array(est_data[:,0],dtype=float)
    est_easting = np.interp(est_time,gps.time,gps.easting)
    est_northing = np.interp(est_time,gps.time,gps.northing)

    # calculate pulse bearing
    est_bearing = np.arctan2(est_easting-float(site.easting), 
                             est_northing-float(site.northing))*180/np.pi

    print "Inserting"
    cur.executemany('''INSERT INTO True_Position 
                              (estID, Cal_InfoID, easting, northing, bearing) 
                       VALUES (%s, %s, %s, %s, %s)''', 
           [ (est_data[j,1], cal_id, est_easting[j], 
              est_northing[j], est_bearing[j]) for j in range(num_records) ])


