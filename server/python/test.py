# Testing, testing ... 

import utm
import util

db_con = util.get_db('writer')

cur = db_con.cursor()

cur.execute('SELECT id, latitude, longitude FROM qraat.sitelist')

for (id, lat, lon) in map(lambda(id, lat, lon) : (id, float(lat), float(lon)), cur.fetchall()): 
  (_, _, zone, letter) = utm.from_latlon(lat, lon)
  cur.execute("UPDATE qraat.sitelist SET zone='%02d%s' WHERE id=%d" % (zone, letter, id))








