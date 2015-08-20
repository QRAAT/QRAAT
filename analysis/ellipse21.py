#!/usr/bin/python

import MySQLdb
import sys
import math
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from pylab import figure, show, rand
from matplotlib.patches import Ellipse
from decimal import Decimal
from matplotlib.collections import EllipseCollection
from datetime import datetime
from matplotlib.colors import LogNorm
from operator import itemgetter

'''
Command line
python "script's name" DEPLOYMENT TIMESTAMP_INI TIMESTAMP_FIN W LIMIT ECC_THRESHOLD AREA_THRESHOLD
'''

#######################
# Database connection #
#######################
# Frontend server
'''
# LAN
# Pipe: ssh -N -L 13306:localhost:3306 eder@192.168.220.163
HOST = "127.0.0.1"
PORT = 13306
USER = "eder"
PASSWD = "K34dV6L9"
DB = "qraat"
'''

# Local (My Virtual Machine)
HOST = "127.0.0.1"
PORT = 3306
USER = "root"
PASSWD = "qraat"
DB = "qraat"

##########################
BEACON = '60'       # if you change this value, you probably should change beacon's coordinates (BEACON_X e BEACON_Y)
BEACON_X = 574296.45
BEACON_Y = 4260910.87
DEPLOYMENT = BEACON # deploymentID - BEACON VALUE, ONLY FOR TEST PURPOSES!!!
TIMESTAMP_INI = 0.0
TIMESTAMP_FIN = 0.0
W = '95' 
LIMIT = 0           # limit of rows returned by the queries 3,4, and 5
ECC_THRESHOLD = 0.97  # eccentricity threshold
AREA_THRESHOLD = 4000 # area threshold
SITES = []
BOUNDS_XY = []
DATA = []
CMAP = 'YlOrRd'     # colormap
NUM_POINTS = 0      # total of points returned by the query
NUM_POINTS_REM = 0  # number of points that remain after filter
PLOT_HIST = 0       # True (1) to plot histograms (Eccentricity and Area), False (0) to don't
PLOT_ECC_AREA = 0   # True (1) to plot scatter (Eccentricity Vs Area), False (0) to don't
PLOT_DISTINCT = 0   # True (1) to plot points that are not in track_pos, False (0) to don't
PLOT_TRACK_POS = 0  # True (1) to plot points that are in track_pos, False (0) to don't
PLOT_GROUP_SITES = 0 # True (1) to plot positions by group of sites, False (0) to don't
PLOT_POS_BY_SITE = 0 # True (1) to plot positions by site, False (0) to don't
PRINT_DATA = 0      # True (1) to print the data, False (0) to don't
PRINT_BEACON_DIST = 0 # True (1) to print distance from points to beacon, False (0) to don't
SHOW_PLOT = 0       # True (1) to show plots, False (0) to don't
FIG_SIZE = (16.0, 10.0)
BEACON_DIST = []    # it will store distance from points to beacon
POS_BY_SITES = []


def main():
  global DEPLOYMENT
  global TIMESTAMP_INI
  global TIMESTAMP_FIN
  global W
  global LIMIT
    
  # get args passed by command line
  getArgs()    
  if TIMESTAMP_INI == 0.0 or TIMESTAMP_FIN == 0.0:    
    # get the minimum and maximum values for timestamp in position table
    query =  "SELECT  MIN(timestamp), MAX(timestamp) \
              FROM    position  \
              WHERE   deploymentID = " + DEPLOYMENT + ";"
    timest = runQuery(1, query)
    useData(1, query,  timest)
    
  # select the sites which are actives
  query = "SELECT * FROM site WHERE easting > 0.00 AND northing > 0.00;"
  sites = runQuery(2, query)
  useData(2, query,  sites)
  
  # get the data to plot the ellipses (WITHOUT track_pos)
  query =  "SELECT  p.timestamp,   p.easting,   p.northing,   c.lambda1,   c.lambda2,   c.alpha,   c.w" + W + ", p.ID \
            FROM    \
                    position as p,   \
                    covariance as c \
            WHERE   p.ID = c.positionID AND   \
                    p.deploymentID = " + DEPLOYMENT + " AND   \
                    UPPER(c.status) = 'OK' AND  \
                    p.timestamp >= " + str(TIMESTAMP_INI) + " AND   \
                    p.timestamp <= " + str(TIMESTAMP_FIN)
  query = getLimit(3, query)
  data1 = runQuery(3, query)
  if data1:
    useData(3, query,  data1)
  else:
    print "\n\n#############################"
    print "#   No data for query #" + str(3) + "!   #"
    print "#############################\n\n"
    print query
    quit()
  
  print '##### Finished #####\n\n'
  
  
def getLimit(queryNum, query):
  global LIMIT
  global DATA
  global TIMESTAMP_INI
  
  if queryNum == 3 and LIMIT > 0:
    query = query + " LIMIT " + LIMIT
  elif (queryNum == 4 or queryNum == 5) and LIMIT > 0:
    TIMESTAMP_FIN = max([row[0] for row in DATA])
    #np.float64(max([row[5] for row in SITES])
  query = query + ";"
  return query
  
  
def runQuery(queryNum, query):  
  global HOST
  global PORT
  global USER
  global PASSWD
  global DB
  
  print '##### Connecting database #####'
  db = connect_db(HOST, PORT, USER, PASSWD, DB)
  if db:
    try:
      print '##### Database connection complete #####'
      print '      Run Query:'
      print queryNum, query
      # prepare a cursor object using cursor() method
      cursor = db.cursor()
      # execute SQL query using execute() method.
      # cursor.execute("SELECT VERSION()")
      cursor.execute(query)
      data = cursor.fetchall()
      # disconnect from server
      db.close()
      print '##### Database connection closed #####'
    except MySQLdb.Error, e:
      sys.stderr.write("[ERROR] %d: %s\n" % (e.args[0], e.args[1]))      
    return data  

  
def useData(queryNum, query, data):
  global TIMESTAMP_INI
  global TIMESTAMP_FIN
  global SITES
  
  if queryNum == 1:
    tsIni = str(data[0][0])
    tsFin = str(data[0][1])
    if tsIni <> 'None' and TIMESTAMP_INI == 0.0:
      TIMESTAMP_INI = tsIni
    if tsFin <> 'None' and TIMESTAMP_FIN == 0.0:
      TIMESTAMP_FIN = tsFin
  elif queryNum == 2:
    SITES = data
  elif queryNum == 3:
    if data:
      useDataQ3(query, data)
    else:
      print '##### There is no data for this query! #####'
      quit()
  elif queryNum == 4:
    # plot the points that are NOT in track_pos
    dist = getDistinct(data)
    if dist:
      dataDist = getEllipses(dist)
      print '\n\n##### Plotting ellipses which are NOT in track_pos #####'
      plotEllipses(dataDist, 'Only points which are NOT in track_pos')
  elif queryNum == 5:
    # plot the points that ARE in track_pos
    if data:
      data2 = getEllipses(data)
      print '\n\n##### Plotting ellipses which ARE in track_pos #####'
      plotEllipses(data2, 'Only points which ARE in track_pos')
  elif queryNum == 6:
    # plot position by group of sites
    if data:
      useDataQ6(data)


def useDataQ6(data):
  global FIG_SIZE
  global DEPLOYMENT
  global POS_BY_SITES
  global PLOT_GROUP_SITES
  posBySite = []

  groups = getGroupsOfSites(data)
  
  if PLOT_GROUP_SITES:
    nr = 1
    print '##### Plotting positions according to their group of sites #####'
    for g1 in groups:
      x = []
      y = []
      color = []   
      getPosBySite(g1)
      for g2 in g1:    
        x.append(g2[5]) # easting
        y.append(g2[6]) # northing
        color.append(g2[9]) # distance from beacon
      fig = figure(figsize = FIG_SIZE)
      ax = plotScatter(fig, x, y, color, 111)
      siteNames = plotSitesByGroup(ax, g1)
      stitle = "POSITION BY GROUP OF SITES\n Group of Sites:\n" + siteNames
      figName = 'dep' + DEPLOYMENT + '_sites_group' + str(nr) + '.png'
      setFigure(fig, stitle, figName)
      nr = nr + 1
  
  if not PLOT_GROUP_SITES and PLOT_POS_BY_SITE:
      for g1 in groups:
        getPosBySite(g1)
  
  if POS_BY_SITES: 
    xPos = []
    yPos = []
    colorPos = []
    POS_BY_SITES.sort()
    indexSite = POS_BY_SITES[0][0]
    
    for site in POS_BY_SITES:
      templist = site[10]
      lastelement = templist[len(templist)-1]
      for s in templist:
        if site[0] == indexSite:
          xPos.append(s[5]) # easting
          yPos.append(s[6]) # northing
          colorPos.append(s[9]) # distance from beacon
          siteIDname = 'POSITIONS BY SITE\n' + \
                      str(site[0]) + ' - ' + site[1] + ' - ' + site[2] + \
                      '\nNumber of Points: ' + str(len(xPos)) + \
                      '     Total of Points: ' + str(NUM_POINTS)
        if (site[0] != indexSite) or (s == lastelement):
          fig = figure(figsize = FIG_SIZE)
          ax = plotScatter(fig, xPos, yPos, colorPos, 111)
          ax.scatter(site[5], site[6], s = 200, c = 'yellow', marker = '>')
          figName = 'dep' + DEPLOYMENT + '_pos_' + site[1] + '.png'
          setFigure(fig, str(siteIDname), figName)
          indexSite = site[0]
          xPos = []
          yPos = []
          colorPos = []
          xPos.append(s[5]) # easting
          yPos.append(s[6]) # northing
          colorPos.append(s[9]) # distance from beacon
      
  
def getPosBySite(group):
  global SITES
  global POS_BY_SITES
  
  for s in SITES:
    # if the siteID is in the group of sites
    s = list(s)
    if s[0] in group[0][8]:
      s.append(group)
      POS_BY_SITES.append(s)

  
def useDataQ3(query, data):
  global TIMESTAMP_INI
  global TIMESTAMP_FIN
  global DATA
  global SHOW_PLOT
  global PRINT_DATA
  global W
  global DEPLOYMENT
  global PLOT_HIST
  global PLOT_ECC_AREA
  global PLOT_DISTINCT
  global PLOT_TRACK_POS
  dataTrackPos = []
  
  # get the data to plot the ellipses (WITH track_pos)
  queryTrackPos =  "SELECT  p.timestamp,   p.easting,   p.northing,   c.lambda1,   c.lambda2,   c.alpha,   c.w" + W + ", p.ID \
            FROM    \
                    position as p,   \
                    covariance as c, \
                    track_pos as t \
            WHERE   p.ID = c.positionID AND   \
                    p.ID = t.positionID AND   \
                    p.deploymentID = " + DEPLOYMENT + " AND   \
                    UPPER(c.status) = 'OK' AND  \
                    p.timestamp >= " + str(TIMESTAMP_INI) + " AND  \
                    p.timestamp <= " + str(TIMESTAMP_FIN)
  if PRINT_DATA:
    printDataDB(data)
  else:
    print '\nNOTE: IF YOU WANT TO PRINT ALL THE DATA, CHANGE THE VALUE OF GLOBAL "PRINT_DATA" FOR TRUE OR 1!\n'
  data2 = getEllipses(data)
  if data2:
    print '##### Plotting ellipses #####'
    plotEllipses(data2, 'Without check track_pos')
  if DEPLOYMENT == BEACON:
    getBeaconData(query, data2)
  if PLOT_HIST:
    print '##### Plotting histograms #####'
    plotHistogram(data2)      
  else:
    print '\nNOTE: IF YOU WANT TO PLOT THE HISTOGRAMS, CHANGE THE VALUE OF GLOBAL "PLOT_HIST" FOR TRUE OR 1!\n'
  if PLOT_ECC_AREA:
    print '##### Plotting eccentricity vs area #####'
    plotScatterEccAr(data2)
  else:
    print '\nNOTE: IF YOU WANT TO PLOT ECCENTRICITY Vs AREA, CHANGE THE VALUE OF GLOBAL "PLOT_ECC_AREA" FOR TRUE OR 1!\n'
  if PLOT_DISTINCT:
    DATA = data
    # plot the points that are NOT in track_pos
    if dataTrackPos:
      useData(4, query, dataTrackPos)
    else:
      queryTrackPos = getLimit(4, queryTrackPos)
      dataTrackPos = runQuery(4, queryTrackPos)
      useData(4, query, dataTrackPos)
  else:
    print '\nNOTE: IF YOU WANT TO PLOT DISTINCT POINTS, CHANGE THE VALUE OF GLOBAL "PLOT_DISTINCT" FOR TRUE OR 1 AND DO NOT SET A LIMIT!\n'
  if PLOT_TRACK_POS:
    # plot the points that ARE in track_pos
    if dataTrackPos:
      useData(5, query, dataTrackPos)
    else:
      queryTrackPos = getLimit(5, queryTrackPos)
      dataTrackPos = runQuery(5, queryTrackPos)
      useData(5, query, dataTrackPos)
  else:
    print '\nNOTE: IF YOU WANT TO PLOT THE TRACK_POS, CHANGE THE VALUE OF GLOBAL "PLOT_TRACK_POS" FOR TRUE OR 1 AND DO NOT SET A LIMIT!\n'
  if SHOW_PLOT:
    show()


def getBeaconData(query, data):
  global BEACON_DIST
  global PRINT_BEACON_DIST
  
  sitesByPos = getSitesByPos(data)
  distFromBeacon = appendDistFromBeacon(sitesByPos)
  useData(6, query, distFromBeacon)
  if BEACON_DIST > 0:
    print '##### Plotting eccentricity vs distance from beacon #####'
    plotScatDistBeacon('ecc', data, BEACON_DIST)
    print '##### Plotting area vs distance from beacon #####'
    plotScatDistBeacon('area', data, BEACON_DIST)
    if PRINT_BEACON_DIST:
      print '\n\n##### Print distance from beacon #####'
      print 'Minimum: ' + str(min(BEACON_DIST)), '     Maximum: ' + str(max(BEACON_DIST)), '     Average: ' + str(np.mean(BEACON_DIST)), '\n'
      for d in BEACON_DIST:
        print d
      print '\n\n'
    else:
      print '\nNOTE: IF YOU WANT TO PRINT THE DISTANCE FROM BEACON, CHANGE THE VALUE OF GLOBAL "PRINT_BEACON_DIST" FOR TRUE OR 1!\n'


def printDataDB(data):
  print '##### Print data #####'
  print '      Total of points: ' + str(len(data)) + '\n\n'
  print 'Timestamp', '\tEasting', '\tNorthing', '\tLambda1', '\tLambda2', '\tAlpha', '\tW', '\tPositionID'
  for row in data:
    '''
    row[0] = timestamp
    row[1] = easting
    row[2] = northing
    row[3] = lambda1
    row[4] = lambda2
    row[5] = alpha
    row[6] = w
    row[7] = positionID
    '''
    print row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
  print '\n\n##### Print complete #####'   
    
    
def plotSitesByGroup(ax, group):
  global SITES
  xSite = []
  ySite = []
  siteNames = ''
  
  # each group
  for g in group[0][8]:
    for s in SITES:
      # if the site exists in SITES
      if g == s[0]:
        # get its coordinates
        xSite.append(s[5])
        ySite.append(s[6])
        sName = '[' + s[1] + ' - ' + s[2] + ']'
    siteNames = siteNames + sName + '   '
  # plot sites according to groups, using a different color 
  ax.scatter(xSite, ySite, s = 200, c = 'yellow', marker = '>')
  return siteNames
  
  
def getGroupsOfSites(data):
  group = []
  for index1 in range(len(data)):
    # if it doesn't have a group yet
    if data[index1][10] == 0:
      # insert it into a group
      group.append([])
      group[len(group) - 1].append(data[index1])
      # flag as having a group
      data[index1][10] = 1
      # start to compare if is the same group from next position
      index2 = index1 + 1
      for index2 in range(len(data)):
        # if it doesn't have a group yet
        if data[index2][10] == 0:
          # check if the sites are the same
          if len(data[index1][8]) == len(data[index2][8]) and len(set(data[index1][8]) - set(data[index2][8])) == 0:
            group[len(group) - 1].append(data[index2])
            # flag as having a group
            data[index2][10] = 1
  return group


def appendDistFromBeacon(sitesByPos):
  global BEACON_DIST
  global BEACON_X
  global BEACON_Y
  '''
  s[5] = Easting (x)
  s[6] = Northing (y)
  '''
  # get the distance between the beacon and each one of the points
  if len(BEACON_DIST) == 0:
    print '##### Appending distance from beacon #####'
    for s in sitesByPos:
      dist = getDistanceAB(BEACON_X, BEACON_Y, s[5], s[6])
      BEACON_DIST.append(dist)
      s.append(dist)
      s.append(0) # it'll be used to check the groups of sites in useData(queryNum, query, data)
  return sitesByPos
  

def getDistinct(dtTrackPos):
  global DATA  
  
  dataPosition = DATA
  dataTrackPos = dtTrackPos
  distinct = []
  distinct = diff(dataPosition, dataTrackPos)
  return distinct


def diff(list1, list2):
  c = set(list1).union(set(list2))
  d = set(list1).intersection(set(list2))
  return list(c - d)


def connect_db(host, port, user, password, db):
  try:
    return MySQLdb.connect(host=host, port=port, user=user, passwd=password, db=db)
  except MySQLdb.Error, e:
    sys.stderr.write("[ERROR] %d: %s\n" % (e.args[0], e.args[1]))
  return False
  
  
def getEllipses(data):
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global NUM_POINTS
  global NUM_POINTS_REM
  global PRINT_DATA
  ellipses = []
  data2 = []
  
  for d in data:
    '''
    d[1] = easting
    d[2] = northing
    d[3] = lambda1
    d[4] = lambda2
    d[5] = alpha
    d[6] = w
    d[7] = positionID
    
    IMPORTANT:  as W has some negative values in the covariance table, 
                we are getting errors when trying to calculate the majorAxis and minorAxis.
                Todd will check how we are getting W.
                For now, we will just get the absolute value of it!
    '''
    majorAxis = math.sqrt(d[3] * abs(d[6])) # math.sqrt(lambda1 * W)
    minorAxis = math.sqrt(d[4] * abs(d[6])) # math.sqrt(lambda2 * W)
    alpha = d[5] * 180 / math.pi # angle = VALUE * 180/math.pi (convert from radians to degrees) 
    eccentricity = math.sqrt(1 - (pow(minorAxis, 2)/pow(majorAxis, 2)))
    area = math.pi * (majorAxis/2) * (minorAxis/2)
    # it will plot only the ellipses with the eccentricity <= than the threshold
    if eccentricity <= ECC_THRESHOLD and area <= AREA_THRESHOLD:
      data2.append([majorAxis, minorAxis, alpha, eccentricity, area, d[1], d[2], d[7]])
      ellipses.append(Ellipse(xy = [d[1], d[2]], width = majorAxis, height = minorAxis, angle = alpha))
  NUM_POINTS = len(data)      # total of points returned by the query
  NUM_POINTS_REM = len(data2) # number of points that remain after filter
  if data2:
    if PRINT_DATA:
      printDataEllipses(data2)
    return data2
  else:
    print "\n##### No data to plot! Try again using other thresholds. #####\n"
    quit()

    
def printDataEllipses(data):
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global NUM_POINTS
  global NUM_POINTS_REM
  
  print '##### Print ellipses data #####'
  print '      Eccentricity Threshold: ' + str(ECC_THRESHOLD), '      Area Threshold: ' + str(AREA_THRESHOLD)
  print '      Total of points after filter: ' + str(len(data)), '(Percentage: ' + str(NUM_POINTS_REM * 100 / NUM_POINTS) + '%)\n\n'
  print 'Major Axis', '\tMinor Axis', '\tAlpha', '\tEccentricity', '\tArea', '\tEasting', '\tNorthing', '\tPositionID'
  for d in data:
    '''
    d[0] = majorAxis
    d[1] = minorAxis
    d[2] = alpha
    d[3] = eccentricity
    d[4] = area
    d[5] = easting
    d[6] = northing
    d[7] = positionID
    '''
    print d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7]
  print '\n\n##### Print ellipses data complete #####'
    
  
def plotEllipses(data, title):
  global DEPLOYMENT
  global TIMESTAMP_INI
  global TIMESTAMP_FIN
  global W
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global BOUNDS_XY
  global PLOT_HIST
  global PLOT_ECC_AREA
  global FIG_SIZE
  global CMAP
  global FIG_SIZE
  global BEACON_X
  global BEACON_Y
  global NUM_POINTS
  global NUM_POINTS_REM
  x = []
  y = [] 
  color = []
  ww = [] # widths (x)
  hh = [] # heights (y)
  aa = [] # angles
  
  for d in data:
    x.append(np.float64(d[5])); # easting
    y.append(np.float64(d[6])); # northing
    color.append(d[3]); # eccentricity will be used to define the color
    ww.append(d[0]) # width = majorAxis
    hh.append(d[1]) # height = minorAxis
    aa.append(d[2]) # angle = alpha
  
  XY = np.vstack((np.array(x),np.array(y))).transpose()
  
  fig = figure(figsize = FIG_SIZE)
  ax1 = fig.add_subplot(121, aspect='equal')  
  # create the ellipses
  ellipseColl = EllipseCollection(ww, hh, aa, units='x', offsets=XY, transOffset=ax1.transData, alpha=0.5)
  ellipseColl.set_array(np.array(color))
  ellipseColl.set_clim(vmin=0, vmax=1)
  ellipseColl.set_cmap(CMAP)
  
  ax1.add_collection(ellipseColl)
  ax1.autoscale_view()
  getBoundsXY(data)
  ax1.set_xlim(BOUNDS_XY[0], BOUNDS_XY[1])
  ax1.set_ylim(BOUNDS_XY[2], BOUNDS_XY[3])  
  ax1.set_title("Ellipses")
  ax1.set_xlabel("Easting")
  ax1.set_ylabel("Northing")
  ax1.grid(True)
    
  # plot sites
  plotSites(ax1)
  plotScatter(fig, x, y, color, 122)
  if DEPLOYMENT == BEACON:
    # plot beacon
    ax1.scatter(BEACON_X, BEACON_Y, s = 300, c = 'green', marker = '8', alpha=0.75)
  stitle = "ELLIPSES: " + title + "\n" \
      "Deployment: " + DEPLOYMENT + \
      "          Timestamp Initial: " + str(datetime.fromtimestamp(float(TIMESTAMP_INI)).strftime('%Y-%m-%d %H:%M:%S')) + \
      "          Timestamp Final: " + str(datetime.fromtimestamp(float(TIMESTAMP_FIN)).strftime('%Y-%m-%d %H:%M:%S')) + \
      "          W: " + W + \
      "          Eccentricity Threshold: " + str(ECC_THRESHOLD) + \
      "          Area Threshold: " + str(AREA_THRESHOLD) + \
      "\nNumber of Points After Filter: " + str(NUM_POINTS_REM) + " from " + str(NUM_POINTS) + " (" + str(NUM_POINTS_REM * 100 / NUM_POINTS) + "%)\n\n"
  figName = 'dep' + DEPLOYMENT + '_ellipses_' + title + '.png'
  setFigure(fig, stitle, figName)
  

def setFigure(fig, stitle, figName):
  # set title
  plt.suptitle(stitle)
  # maximize the image
  mng = plt.get_current_fig_manager()
  mng.resize(*mng.window.maxsize())
  if fig:
    # save the image
    fig.savefig(figName, orientation='landscape', bbox_inches='tight')
  
  
def getDistanceAB(xa, ya, xb, yb):
  dAB = math.sqrt(pow(float(xb) - xa, 2) + pow(float(yb) - ya, 2))
  return dAB


def getSitesByPos(data):
  sitesByPos = []
  
  #print '##### Getting sites by position #####'
  # get the sites used to made a position
  
  query =  "SELECT  p.obj_id, b.siteID \
            FROM    bearing as b, \
                    provenance as p \
            WHERE   p.obj_table = 'position' AND   \
                    b.ID = p.dep_id \
            ORDER BY obj_id;"
  '''
  query = "SELECT  p.obj_id, b.siteID, pos.easting, pos.northing \
          FROM    bearing as b, \
                  provenance as p, \
                  position as pos \
          WHERE   p.obj_table = 'position' AND \
                  b.ID = p.dep_id AND \
                  pos.ID = p.obj_id;"
  '''
  sitesByPos = runQuery(6, query)
  sitesAppended = appendSitesByPos(data, sitesByPos)
  return sitesAppended

  
def appendSitesByPos(data, sitesByPos):
  global NUM_POINTS_REM
  
  i = 1
  print '##### Appending sites by position #####'
  # sort data by positionID
  #sorted(data, key = itemgetter(7))
  # for each positionID in data, get the sites in sitesByPos   
  for d in data:
    d.append([])
    print str(i) + ' from ' + str(NUM_POINTS_REM)
    i = i + 1
    for s in sitesByPos:
      # d[7] = positionID in data 
      # s[0] = positionID in sitesByPos
      if d[7] == s[0]:
        # append site to data
        d[8].append(s[1])
      elif d[7] < s[0]:
        break
  return data


def plotScatDistBeacon(type, data, beaconDist):
  global FIG_SIZE
  global BEACON_DIST
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global NUM_POINTS
  global NUM_POINTS_REM
  global DEPLOYMENT
  global CMAP
  x = []
  y = BEACON_DIST
  color = []
  size = []
  
  if type == 'ecc':
    index1 = 3 # eccentricity
    index2 = 4 # area
    title1 = 'Eccentricity'
    title2 = 'Area (square meters)'
  if type == 'area':
    index1 = 4 # area
    index2 = 3 # eccentricity
    title1 = 'Area (square meters)'
    title2 = 'Eccentricity'
  for d in data:
    x.append(d[index1]) # x axis = eccentricity/area
    color.append(d[index2]); # eccentricity/area will be used to define the color
  fig = figure(figsize = FIG_SIZE)
  ax = fig.add_subplot(111)  
  ax.set_xlabel(title1)
  ax.set_ylabel("Distance from Beacon (meters)")
  ax.grid(True)
  # plot points
  if type == 'ecc':
    norm = mpl.colors.Normalize(vmin=0, vmax=max(color))
  else:
    norm = mpl.colors.Normalize(vmin=0, vmax=1)
  ax.scatter(x, y, s = 100, c = color, cmap=CMAP, norm=norm, alpha=0.5)
  # legend
  cax = fig.add_axes([0.95, 0.25, 0.02, 0.5])
  cb = mpl.colorbar.ColorbarBase(cax, cmap=CMAP, norm=norm, spacing='proportional')
  stitle = title1 + " Vs Distance from Beacon\n" \
      "Eccentricity Threshold: " + str(ECC_THRESHOLD) + \
      "          Area Threshold: " + str(AREA_THRESHOLD) + \
      "\nNumber of Points After Filter: " + str(NUM_POINTS_REM) + " from " + str(NUM_POINTS) + " (" + str(NUM_POINTS_REM * 100 / NUM_POINTS) + "%)" \
      "\nColors are based on: " + title2
  figName = 'dep' + DEPLOYMENT + '_' + type + 'XdistBeacon.png'
  setFigure(fig, stitle, figName)

  
def plotScatter(fig, x, y, color, display_pos):
  global CMAP
  global BOUNDS_XY
  global BEACON_X
  global BEACON_Y
  
  ax = fig.add_subplot(display_pos, aspect='equal')
  ax.set_xlim(BOUNDS_XY[0], BOUNDS_XY[1])
  ax.set_ylim(BOUNDS_XY[2], BOUNDS_XY[3])
  ax.set_title("Points")
  ax.set_xlabel("Easting")
  ax.set_ylabel("Northing")
  ax.grid(True)
  # plot points
  ax.scatter(x, y, s = 100, c = color, cmap=CMAP, alpha=0.5, vmin=0, vmax=1)  
  # plot sites
  plotSites(ax)
  # plot beacon
  if DEPLOYMENT=='60':
    ax.scatter(BEACON_X, BEACON_Y, s = 300, c = 'green', marker = '8', alpha=0.75)
    return ax


def plotScatterEccAr(data):
  global FIG_SIZE
  global BEACON_DIST
  global CMAP
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global NUM_POINTS
  global NUM_POINTS_REM
  global DEPLOYMENT
  x = []
  y = [] 
  color = []
  size = []
  beaconLen = len(BEACON_DIST)
  
  for d in data:
    x.append(d[3]) # x axis = eccentricity
    y.append(d[4]) # y axis = area
    if beaconLen == 0:
      color.append(d[3]); # eccentricity will be used to define the color
  if beaconLen > 0:
    color = BEACON_DIST # distance from beacon will be used to define the color
  fig = figure(figsize = FIG_SIZE)
  ax = fig.add_subplot(111)  
  ax.set_xlabel("Eccentricity")
  ax.set_ylabel("Area (square meters)")
  ax.grid(True)
  # plot points
  if beaconLen == 0:
    norm = mpl.colors.Normalize(vmin=0, vmax=1)
    text = "Colors are based on: Eccentricity"
  else:
    norm = mpl.colors.Normalize(vmin=0, vmax=max(BEACON_DIST))
    text = "Colors are based on: Distance from beacon (meters)"
  ax.scatter(x, y, s = 100, c = color, cmap=CMAP, norm=norm, alpha=0.5)
  # legend
  cax = fig.add_axes([0.95, 0.25, 0.02, 0.5])
  cb = mpl.colorbar.ColorbarBase(cax, cmap=CMAP, norm=norm, spacing='proportional')  
  stitle = "ECCENTRICITY Vs AREA\n" \
      "Eccentricity Threshold: " + str(ECC_THRESHOLD) + \
      "          Area Threshold: " + str(AREA_THRESHOLD) + \
      "\nNumber of Points After Filter: " + str(NUM_POINTS_REM) + " from " + str(NUM_POINTS) + " (" + str(NUM_POINTS_REM * 100 / NUM_POINTS) + \
      "%)\n" + text
  figName = 'dep' + DEPLOYMENT + '_eccXarea.png'
  setFigure(fig, stitle, figName)
  
  
def plotSites(ax):
  global SITES
  xSite = []
  ySite = [] 
  
  # get the sites position to plot them
  for s in SITES:
    xSite.append(s[5]); 
    ySite.append(s[6]);
  # plot sites
  ax.scatter(xSite, ySite, s = 200, c = 'blue', marker = '>', alpha=0.75)

  
def plotHistogram(data):
  global FIG_SIZE
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global NUM_POINTS
  global NUM_POINTS_REM
  global DEPLOYMENT
  area = []
  ecc = []
  '''
  d2[0] = majorAxis
  d2[1] = minorAxis
  d2[2] = alpha
  d2[3] = eccentricity
  d2[4] = area
  d2[5] = easting
  d2[6] = northing
  '''
  for d in data:
    ecc.append(d[3])
    area.append(d[4])
  fig = figure(figsize = FIG_SIZE)
  # eccentricity
  ax1 = fig.add_subplot(121)
  ax1.set_title("Histogram - Eccentricity")
  ax1.set_xlabel("Eccentricity")
  ax1.set_ylabel("Number of points")
  ax1.grid(True)
  ax1.hist(ecc, bins = 50, facecolor='red')
  # area
  ax2 = fig.add_subplot(122)
  ax2.set_title("Histogram - Area")
  ax2.set_xlabel("Area (square meters)")
  ax2.set_ylabel("Number of points")
  ax2.grid(True)
  ax2.hist(area, bins = 50, facecolor='orange')
  stitle = "HISTOGRAMS\n" \
      "Eccentricity Threshold: " + str(ECC_THRESHOLD) + \
      "          Area Threshold: " + str(AREA_THRESHOLD) + \
      "\nNumber of Points After Filter: " + str(NUM_POINTS_REM) + " from " + str(NUM_POINTS) + " (" + str(NUM_POINTS_REM * 100 / NUM_POINTS) + "%)\n\n"
  figName = 'dep' + DEPLOYMENT + '_histograms.png'
  setFigure(fig, stitle, figName)
  
  
def getBoundsXY(data):
  global BOUNDS_XY
  
  # get bounds for the plot
  minXs = np.float64(min([row[5] for row in SITES]) - 200)
  maxXs = np.float64(max([row[5] for row in SITES]) + 200)
  minYs = np.float64(min([row[6] for row in SITES]) - 200)
  maxYs = np.float64(max([row[6] for row in SITES]) + 200)
  
  # get bounds for the plot
  minXd = np.float64(min([row[5] for row in data]) - 200)
  maxXd = np.float64(max([row[5] for row in data]) + 200)
  minYd = np.float64(min([row[6] for row in data]) - 200)
  maxYd = np.float64(max([row[6] for row in data]) + 200)
  
  if minXs < minXd:
    BOUNDS_XY.append(minXs)
  else:
    BOUNDS_XY.append(minXd)
  if maxXs > maxXd:
    BOUNDS_XY.append(maxXs)
  else:
    BOUNDS_XY.append(maxXd)
  if minYs < minYd:
    BOUNDS_XY.append(minYs)
  else:
    BOUNDS_XY.append(minYd)
  if maxYs > maxYd:
    BOUNDS_XY.append(maxYs)
  else:
    BOUNDS_XY.append(maxYd)
  
  
def getArgs():
  global DEPLOYMENT
  global TIMESTAMP_INI
  global TIMESTAMP_FIN
  global W
  global LIMIT
  global ECC_THRESHOLD
  global AREA_THRESHOLD
  global PLOT_DISTINCT
  global PLOT_TRACK_POS
  
  if len(sys.argv) == 8:
    if sys.argv[1] <> '-':
      DEPLOYMENT =  sys.argv[1]
    if sys.argv[2] <> '-':
      TIMESTAMP_INI = sys.argv[2]
    if sys.argv[3] <> '-':
      TIMESTAMP_FIN = sys.argv[3]
    if sys.argv[4] <> '-':
      W =  sys.argv[4]
    if sys.argv[5] <> '-':
      LIMIT = sys.argv[5]
      print '\nNOTE: SETTING "LIMIT", TRACK_POS AND DISTINCT DATA WILL NOT BE PLOTTED! PLOTS WOULD BE INCONSISTENT.\n'
      PLOT_DISTINCT = 0
      PLOT_TRACK_POS = 0
    if sys.argv[6] <> '-':
      ECC_THRESHOLD =  Decimal(sys.argv[6])
    if sys.argv[7] <> '-':
      AREA_THRESHOLD =  Decimal(sys.argv[7])
  else:
    print """\n##### List of arguments: #####"""
    print """\npython "script's name" DEPLOYMENT(1) TIMESTAMP_INI(2) TIMESTAMP_FIN(3) W(4) LIMIT(5) ECC_THRESHOLD(6) AREA_THRESHOLD(7)\n\n"""
    print """##### You can also use the default values typing: #####"""
    print """\npython "script's name" - - - - - - -\n\n"""
    print """##### Defualt values: #####"""
    print "\nDEPLOYMENT =  " + BEACON + \
          "     TIMESTAMP_INI = min(TIMESTAMP)" \
          "     TIMESTAMP_FIN = max(TIMESTAMP)" \
          "     W =  " + W + \
          "     LIMIT = 0" \
          "     ECC_THRESHOLD =  " + str(ECC_THRESHOLD) + \
          "     AREA_THRESHOLD = " + str(AREA_THRESHOLD) + "\n\n"
    quit()

    
if __name__ == "__main__":
  main()
