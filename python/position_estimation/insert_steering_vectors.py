import MySQLdb
import getpass
import numpy as np

mysql_host = "169.237.92.155"
#mysql_host = "10.253.1.55"
mysql_user = "todd"
mysql_db = "qraat"
cal_id=1
site_id=8
sv_csv = "ID8_pat.csv"

#open database
password = getpass.getpass("Enter password for user: {0} for db: {1} at {2}\nPassword: ".format(mysql_user,mysql_db,mysql_host))
db = MySQLdb.connect(mysql_host, mysql_user, password, mysql_db)
db_cursor = db.cursor()

sv = np.genfromtxt(sv_csv,delimiter=",")
db_cursor.executemany("INSERT INTO Steering_Vectors (Cal_InfoID, SiteID, Bearing, sv1r, sv1i, sv2r, sv2i, sv3r, sv3i, sv4r, sv4i) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ;",[ (cal_id, site_id, sv[j,0], sv[j,1], sv[j,2], sv[j,3], sv[j,4], sv[j,5], sv[j,6], sv[j,7], sv[j,8]) for j in range(sv.shape[0]) ])

db.close()
