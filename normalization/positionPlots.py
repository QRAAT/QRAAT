import MySQLdb
import numpy as np
import matplotlib.pyplot as plt
import time


def errorCalculation(t, e, n):
  
  db_con = MySQLdb.connect(user="root", db="qraat")
  cur = db_con.cursor()
  cur.execute("""
                 SELECT timestamp, easting, northing
                 FROM gps_data
                 WHERE deploymentID = 142
                 AND timestamp = %s;
              """%(t))
  x = cur.fetchall()
  if (len(x) == 1):
    return np.sqrt((e - float(x[0][1]))**2 + (n - float(x[0][2]))**2)
  else:
    cur.execute("""
                 SELECT timestamp, easting, northing
                 FROM gps_data
                 WHERE deploymentID = 142
                 AND timestamp < %s
                 ORDER BY timestamp DESC
                 LIMIT 1;
              """%(t))
    x1 = map(float,cur.fetchall()[0])
    cur.execute("""
                 SELECT timestamp, easting, northing
                 FROM gps_data
                 WHERE deploymentID = 142
                 AND timestamp > %s
                 ORDER BY timestamp
                 LIMIT 1;
              """%(t))
    x2 = map(float,cur.fetchall()[0])
    x = [x1[1]+(x2[1] - x1[1])/(x2[0] - x1[0])*(t - x1[0]),
         x1[2]+(x2[2] - x1[2])/(x2[0] - x1[0])*(t - x1[0])]
    return np.sqrt((e - x[0])**2 + (n - x[1])**2)
    


def gpsLocationQuery():
  db_con = MySQLdb.connect(user="root", db="qraat")
  cur = db_con.cursor()
  cur.execute("""
                 SELECT easting, northing
                 FROM gps_data
                 WHERE deploymentID = 142
                 AND timestamp >= 1461884300
                 AND timestamp <= 1461886955
                 ORDER BY timestamp;
              """)
  east = []
  north = []
  for row in cur.fetchall():
    east.append(row[0])
    north.append(row[1])
  return east, north

def positionPlot(deploymentID, normalized, likelihood):
  initTime = time.time()
  
  db_con = MySQLdb.connect(user="root", db="qraat")
  cur = db_con.cursor()
  cur.execute("""
                 SELECT timestamp, easting, northing
                 FROM position_non_normalized
                 WHERE deploymentID = %s
                 AND isNormalized = %s
                 AND likelihood > %s
                 ORDER BY timestamp;
              """%(deploymentID, normalized, likelihood))
  eastingArray = []
  northingArray = []
  err = 0
  for row in cur.fetchall():
    eastingArray.append(row[1])
    northingArray.append(row[2])
    if deploymentID == 142:
      err += errorCalculation(float(row[0]), float(row[1]), float(row[2]))


  print 'Took %s seconds.'%(time.time()-initTime)

  plt.plot(eastingArray, northingArray, '.', label = 'calculated positions')
  
  if deploymentID == 142:
    gpsEasting, gpsNorthing = gpsLocationQuery()
    plt.plot(gpsEasting, gpsNorthing, label = 'gps data')
    plt.figtext(0.4,0.02,'The average distance error = %s'%(err/len(eastingArray)))
  plt.xlabel('Easting')
  plt.ylabel('Northing')
  plt.xlim(573723-150, 573723+150)
  plt.ylim(4261870-150, 4261870+150)
  if normalized:
    plt.title('Deployment%s, normalized, likelihood > %s'%(deploymentID,
                                                           likelihood))
  else:
    plt.title('Deployment%s, non-normalized, likelihood > %s'%(deploymentID,
                                                               likelihood))
  plt.show()


def main():
  DeploymentID = 116
##  DeploymentID = 142
  normalized = 1
  likelihood = 0.03
  
  positionPlot(DeploymentID, normalized, likelihood)
  
  
if __name__ == '__main__':
  main()
