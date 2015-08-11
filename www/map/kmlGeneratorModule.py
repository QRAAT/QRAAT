import xml.dom.minidom
import sys
import time
from time import strftime
import math
import pytz
from datetime import datetime, timedelta

def createStyle2(kmlDoc):
  styleElement = kmlDoc.createElement('Style')
  key='point-style'
  styleElement.setAttribute('id', key)
  iconStyleElement = kmlDoc.createElement('IconStyle')
  styleElement.appendChild(iconStyleElement)
  scale= '0.3'
  scaleElement = kmlDoc.createElement('scale')
  scaleElement.appendChild(kmlDoc.createTextNode(scale))
  iconStyleElement.appendChild(scaleElement)
  iconElement = kmlDoc.createElement('Icon')
  iconStyleElement.appendChild(iconElement)
  href= 'http://help.team-logic.com/tl_icons/32x32/bullet_ball_blue.png'
  hrefElement = kmlDoc.createElement('href')
  hrefElement.appendChild(kmlDoc.createTextNode(href))
  iconElement.appendChild(hrefElement)

  labelStyleElement = kmlDoc.createElement('LabelStyle')
  styleElement.appendChild(labelStyleElement)
  color= 'ffffffff'
  colorElement = kmlDoc.createElement('color')
  colorElement.appendChild(kmlDoc.createTextNode(color))
  labelStyleElement.appendChild(colorElement)
  labelScale= '0.0'
  labelScaleElement = kmlDoc.createElement('scale')
  labelScaleElement.appendChild(kmlDoc.createTextNode(labelScale))
  labelStyleElement.appendChild(labelScaleElement)

  lineStyleElement = kmlDoc.createElement('LineStyle')
  styleElement.appendChild(lineStyleElement)
  lineColor= 'ffDA70D6'
  lineColorElement = kmlDoc.createElement('color')
  lineColorElement.appendChild(kmlDoc.createTextNode(lineColor))
  lineStyleElement.appendChild(lineColorElement)

  return styleElement

def createStyle(kmlDoc):
  styleElement = kmlDoc.createElement('Style')
  key='fox-icon'
  styleElement.setAttribute('id', key)
  
  iconStyleElement = kmlDoc.createElement('IconStyle')
  styleElement.appendChild(iconStyleElement)
  iconElement = kmlDoc.createElement('Icon')
  iconStyleElement.appendChild(iconElement)
  href= 'http://orig05.deviantart.net/4c3a/f/2015/096/4/6/fox_fox_fox_fox_fox__stop_being_lazy_ya__bum___by_joribinky-d8ora0v.png'
  hrefElement = kmlDoc.createElement('href')
  hrefElement.appendChild(kmlDoc.createTextNode(href))
  iconElement.appendChild(hrefElement)

  labelStyleElement = kmlDoc.createElement('LabelStyle')
  styleElement.appendChild(labelStyleElement)
  color= 'ffffffff'
  colorElement = kmlDoc.createElement('color')
  colorElement.appendChild(kmlDoc.createTextNode(color))
  labelStyleElement.appendChild(colorElement)
  labelScale= '0.0'
  labelScaleElement = kmlDoc.createElement('scale')
  labelScaleElement.appendChild(kmlDoc.createTextNode(labelScale))
  labelStyleElement.appendChild(labelScaleElement)

  lineStyleElement = kmlDoc.createElement('LineStyle')
  styleElement.appendChild(lineStyleElement)
  lineColor= 'ff0000ff'
  lineColorElement = kmlDoc.createElement('color')
  lineColorElement.appendChild(kmlDoc.createTextNode(lineColor))
  lineStyleElement.appendChild(lineColorElement)

  return styleElement

def createPoints(kmlDoc, epochTime, latitude, longitude):
  # This creates a <Placemark> element for a row of data.
  # A row is a dict.
  placemarkElement = kmlDoc.createElement('Placemark')
  styleUrl= '#point-style'
  styleUrlElement = kmlDoc.createElement('styleUrl')
  styleUrlElement.appendChild(kmlDoc.createTextNode(styleUrl))
  placemarkElement.appendChild(styleUrlElement)

##  print time
##  print type(time)
##  print type(int(time))
##  time = int(time)
##  t=time.gmtime(epochTime)
##  timeString="%s-%s-%s %s:%s:%s"%(strftime("%Y", t),strftime("%m", t),strftime("%d", t),strftime("%H", t),strftime("%M", t),strftime("%S", t))

  ## Time zone will need to be set or queried!!!
  DATA_TIMEZONE = pytz.timezone('America/Los_Angeles')
  timeString = str(DATA_TIMEZONE.normalize(pytz.utc.localize(datetime.utcfromtimestamp(int(epochTime)), is_dst=True).astimezone(DATA_TIMEZONE))) 
  nameElement = kmlDoc.createElement('name')
  nameElement.appendChild(kmlDoc.createTextNode(timeString[0:19]))
  placemarkElement.appendChild(nameElement)
  
  
  extElement = kmlDoc.createElement('ExtendedData')
  placemarkElement.appendChild(extElement)
  
  # Loop through the columns and create a <Data> element for every field that has a value.
  dataElement = kmlDoc.createElement('Data')
  dataElement.setAttribute('name', 'timestamp')
  valueElement = kmlDoc.createElement('value')
  dataElement.appendChild(valueElement)
  valueText = kmlDoc.createTextNode(timeString)
  valueElement.appendChild(valueText)
  extElement.appendChild(dataElement)
  dataElement = kmlDoc.createElement('Data')
  dataElement.setAttribute('name', 'latitude')
  valueElement = kmlDoc.createElement('value')
  dataElement.appendChild(valueElement)
  valueText = kmlDoc.createTextNode(str(latitude))
  valueElement.appendChild(valueText)
  extElement.appendChild(dataElement)
  dataElement = kmlDoc.createElement('Data')
  dataElement.setAttribute('name', 'longitude')
  valueElement = kmlDoc.createElement('value')
  dataElement.appendChild(valueElement)
  valueText = kmlDoc.createTextNode(str(longitude))
  valueElement.appendChild(valueText)
  extElement.appendChild(dataElement)
  
  pointElement = kmlDoc.createElement('Point')
  placemarkElement.appendChild(pointElement)
  extrude= '1'
  extrudeElement = kmlDoc.createElement('extrude')
  extrudeElement.appendChild(kmlDoc.createTextNode(extrude))
  pointElement.appendChild(extrudeElement)
  altitudeMode= 'relativeToGround'
  altitudeModeElement = kmlDoc.createElement('altitudeMode')
  altitudeModeElement.appendChild(kmlDoc.createTextNode(altitudeMode))
  pointElement.appendChild(altitudeModeElement)
  coordinates = '%s,%s,1' % (longitude, latitude)
  coorElement = kmlDoc.createElement('coordinates')
  coorElement.appendChild(kmlDoc.createTextNode(coordinates))
  pointElement.appendChild(coorElement)
  return placemarkElement

def createTrack(kmlDoc, timeArray, longitudeArray, latitudeArray):
  placemarkElement = kmlDoc.createElement('Placemark')
  styleUrl= '#fox-icon'
  styleUrlElement = kmlDoc.createElement('styleUrl')
  styleUrlElement.appendChild(kmlDoc.createTextNode(styleUrl))
  placemarkElement.appendChild(styleUrlElement)

  trackName = 'Track'
  nameElement = kmlDoc.createElement('name')
  nameElement.appendChild(kmlDoc.createTextNode(trackName))
  placemarkElement.appendChild(nameElement)
  
  gxBalloonVisibility= '1'
  gxBalloonVisibilityElement = kmlDoc.createElement('gx:balloonVisibility')
  gxBalloonVisibilityElement.appendChild(kmlDoc.createTextNode(gxBalloonVisibility))
  placemarkElement.appendChild(gxBalloonVisibilityElement)

  gxTrackElement = kmlDoc.createElement('gx:Track')
  placemarkElement.appendChild(gxTrackElement)
  altitudeMode = 'clampToGround'
  altitudeModeElement = kmlDoc.createElement('altitudeMode')
  altitudeModeElement.appendChild(kmlDoc.createTextNode(altitudeMode))
  gxTrackElement.appendChild(altitudeModeElement)
  timeLength=len(timeArray)
  for idx, val in enumerate(timeArray):
    whenElement = kmlDoc.createElement('when')
    whenElement.appendChild(kmlDoc.createTextNode(timeArray[idx]))
    gxTrackElement.appendChild(whenElement)
  for idx, val in enumerate(longitudeArray):
    gxCoord = '%s %s'%(longitudeArray[idx], latitudeArray[idx])
    gxCoordElement = kmlDoc.createElement('gx:coord')
    gxCoordElement.appendChild(kmlDoc.createTextNode(gxCoord))
    gxTrackElement.appendChild(gxCoordElement)
    
  return placemarkElement

def circleCoordinate(latitude,longitude,altitude):
  radius = 0.00016
  numberOfPoints = 16
  circleCoordinate = ''
  for i in range(numberOfPoints+1):
    temLatitude = float(latitude) + radius*math.sin(2*math.pi*i/numberOfPoints)
    temLongitude = float(longitude) + radius*math.cos(2*math.pi*i/numberOfPoints)
    coor = '%s,%s,%s '%(temLongitude,temLatitude,altitude+430)
    circleCoordinate=circleCoordinate+coor
  return circleCoordinate

def createPlacemark(kmlDoc, altitude, latitude, longitude, maxAltitude):
  placemarkElement = kmlDoc.createElement('Placemark')

  styleElement = kmlDoc.createElement('Style')
  placemarkElement.appendChild(styleElement)
  polyStyleElement = kmlDoc.createElement('PolyStyle')
  styleElement.appendChild(polyStyleElement)

  colorCode = 255-235*float(altitude)/maxAltitude
  hexColorCode = format(int(math.floor(colorCode)),'x')
  if colorCode<16:
    color= 'ff000%s00'%(hexColorCode)
  else:
    color= 'ff00%s00'%(hexColorCode)
  colorElement = kmlDoc.createElement('color')
  colorElement.appendChild(kmlDoc.createTextNode(color))
  polyStyleElement.appendChild(colorElement)

  outline= '0'
  outlineElement = kmlDoc.createElement('outline')
  outlineElement.appendChild(kmlDoc.createTextNode(outline))
  polyStyleElement.appendChild(outlineElement)  
  
  polygonElement = kmlDoc.createElement('Polygon')
  placemarkElement.appendChild(polygonElement)
  
  extrude= '1'
  extrudeElement = kmlDoc.createElement('extrude')
  extrudeElement.appendChild(kmlDoc.createTextNode(extrude))
  polygonElement.appendChild(extrudeElement)

  altitudeMode= 'absolute'
  altitudeModeElement = kmlDoc.createElement('altitudeMode')
  altitudeModeElement.appendChild(kmlDoc.createTextNode(altitudeMode))
  polygonElement.appendChild(altitudeModeElement)
  
  outerBoundaryIsElement = kmlDoc.createElement('outerBoundaryIs')
  polygonElement.appendChild(outerBoundaryIsElement)

  LinearRingElement = kmlDoc.createElement('LinearRing')
  outerBoundaryIsElement.appendChild(LinearRingElement)

  coordinates= circleCoordinate(latitude,longitude,altitude)
  coordinatesElement = kmlDoc.createElement('coordinates')
  coordinatesElement.appendChild(kmlDoc.createTextNode(coordinates))
  LinearRingElement.appendChild(coordinatesElement)
  
  return placemarkElement

def calculateAltitude(radius, latitudeArray, longitudeArray):
  arrayLength=len(latitudeArray)
  altitudeArray=[5]*arrayLength
  maxAltitude=5

  ##Count the number of points within the region and find maximum value.
  for i in range(0,arrayLength-1):
    for j in range(i+1,arrayLength):
      distance = math.sqrt(math.pow(latitudeArray[i]-latitudeArray[j],2)+math.pow(longitudeArray[i]-longitudeArray[j],2));
      if (distance<=radius):
        altitudeArray[i]+=2
        altitudeArray[j]+=2
        if (altitudeArray[i]>maxAltitude):
          maxAltitude=altitudeArray[i]
        if (altitudeArray[j]>maxAltitude):
          maxAltitude=altitudeArray[j]
    
  return altitudeArray, maxAltitude

def meanTimeSampling(numberOfIntervals, timeArray, latitudeArray, longitudeArray):
  arrayLength = len(timeArray)
  minimumTime = timeArray[0]
  maximumTime = timeArray[arrayLength-1]

  ##Ensure there is at least a point every hour.
  timeInterval = (maximumTime - minimumTime)/numberOfIntervals
  if (timeInterval>3600):
    timeInterval = 3600
    numberOfIntervals = int(math.ceil((maximumTime - minimumTime)/3600))

  meanTimeArray = []
  meanLatitudeArray = []
  meanLongitudeArray = []
  lastIndex = 0
  for i in range(numberOfIntervals):
    intervalStartTime = minimumTime + timeInterval*i
    intervalEndTime = minimumTime + timeInterval*(i+1)
    sumTime = 0
    sumLatitude = 0
    sumLongitude = 0
    numberOfElement = 0

    ##Find the sum in each interval.
    for j in range(lastIndex,arrayLength):
      if ((intervalStartTime<=timeArray[j])&(timeArray[j]<=intervalEndTime)):
        sumTime += timeArray[j]
        sumLatitude += latitudeArray[j]
        sumLongitude += longitudeArray[j]
        numberOfElement += 1
      elif (timeArray[j]>intervalEndTime):
        lastIndex = j-1
        break

    ##Store the average in an array
    if (numberOfElement != 0):
      meanTimeArray.append(sumTime/numberOfElement)
      meanLatitudeArray.append(sumLatitude/numberOfElement)
      meanLongitudeArray.append(sumLongitude/numberOfElement)
      
  return meanTimeArray, meanLatitudeArray, meanLongitudeArray

def createKML(deploymentID, radius, numberOfIntervals, trackPath, trackLocation, histogram, timeArray, latitudeArray, longitudeArray):

  kmlDoc = xml.dom.minidom.Document()

  ## Add headings to the KML.
  kmlElement = kmlDoc.createElementNS('http://earth.google.com/kml/2.2', 'kml')
  kmlElement.setAttribute('xmlns', 'http://www.opengis.net/kml/2.2')
  kmlElement.setAttribute('xmlns:gx', 'http://www.google.com/kml/ext/2.2')
  kmlElement.setAttribute('xmlns:kml', 'http://www.opengis.net/kml/2.2')
  kmlElement.setAttribute('xmlns:atom', 'http://www.w3.org/2005/Atom')
  kmlElement = kmlDoc.appendChild(kmlElement)
  documentElement = kmlDoc.createElement('Document')
  documentElement = kmlElement.appendChild(documentElement)

  ##Add styles for different content.
  styleElement = createStyle(kmlDoc)
  documentElement.appendChild(styleElement)
  styleElement2 = createStyle2(kmlDoc)
  documentElement.appendChild(styleElement2)

  ##Sample the mean time, latitude, and longitude.
  [meanTimeArray, meanLatitudeArray, meanLongitudeArray] = meanTimeSampling(numberOfIntervals, timeArray, latitudeArray, longitudeArray)

  ##Convert time into Google Earth readable form.
  ## Time zone will need to be set or queried!!!
  DATA_TIMEZONE = pytz.timezone('America/Los_Angeles')
  convertedTime=[]
  for JStime in meanTimeArray:
#      tm=time.gmtime(float(JStime))
#      timeString="%s-%s-%sT%s:%s:%sZ"%(strftime("%Y", t),strftime("%m", t),strftime("%d", t),strftime("%H", t),strftime("%M", t),strftime("%S", t))
#      timeString = strftime("%Y-%m-%dT%H:%M:%SZ",tm)
      timeString = DATA_TIMEZONE.normalize(pytz.utc.localize(datetime.utcfromtimestamp(int(JStime)), is_dst=True).astimezone(DATA_TIMEZONE))
      timeString = str(timeString)[0:10]+'T'+str(timeString)[11:25]
      convertedTime.append(timeString)

  ##Create tracks if the setting is yes.
  if (trackPath=='Yes'):
    trackElement = createTrack(kmlDoc,convertedTime,meanLongitudeArray,meanLatitudeArray)
    documentElement.appendChild(trackElement)

  ##Create track locatoins if the setting is yes.
  if (trackLocation=='Yes'):
    folderElement = kmlDoc.createElement('Folder')
    folderName = 'Track Locations'
    nameElement = kmlDoc.createElement('name')
    nameElement.appendChild(kmlDoc.createTextNode(folderName))
    folderElement.appendChild(nameElement)
    meanArrayLength = len(meanTimeArray)
    for i in range(meanArrayLength):
      placemarkElement = createPoints(kmlDoc, meanTimeArray[i], meanLatitudeArray[i], meanLongitudeArray[i])
      folderElement.appendChild(placemarkElement)
    documentElement.appendChild(folderElement)

  ##Create histogram if the setting is yes.
  if (histogram=='Yes'):
    [altitudeArray, maxAltitude] = calculateAltitude(radius, latitudeArray, longitudeArray)
    folderElement2 = kmlDoc.createElement('Folder')
    folderName2 = 'Histogram'
    nameElement2 = kmlDoc.createElement('name')
    nameElement2.appendChild(kmlDoc.createTextNode(folderName2))
    folderElement2.appendChild(nameElement2)
    arrayLength=len(altitudeArray)
    for i in range(arrayLength):
      placemarkElement = createPlacemark(kmlDoc, altitudeArray[i], latitudeArray[i], longitudeArray[i], maxAltitude)
      folderElement2.appendChild(placemarkElement)
    documentElement.appendChild(folderElement2)

  ##Output the file.
  ##fileName = 'deployment%s_python.kml'%(deploymentID)
  ##kmlFile = open(fileName, 'w')
  ##kmlFile.write(kmlDoc.toprettyxml('  ', newl = '\n', encoding = 'utf-8'))

  return kmlDoc.toprettyxml('  ', newl = '\n', encoding = 'utf-8')

def main(deploymentID, trackPath, trackLocation, histogram, timeArray, latitudeArray, longitudeArray):
  ## Set all the necessary parameters.
  deploymentID = 124
  radius = 0.00016
  numberOfIntervals = 100
  
  #for i in range(len(timeArray)-1):
   # timeArray[i]=float(timeArray[i])
    #latitudeArray[i]=float(latitudeArray[i])
    #longitudeArray[i]=float(longitudeArray[i])
  ## Create kml file with the given parameters.

  return createKML(deploymentID, radius, numberOfIntervals, trackPath, trackLocation, histogram, timeArray, latitudeArray, longitudeArray)

  ## Let user know the file is ready.
  print 'kml is generated'

if __name__ == '__main__':
  sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7]))
