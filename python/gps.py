# gps.py - A class for encapsulating GPS data produced by the yellow
# Garmin GPS unit. This file is part of QRAAT, an automated animal 
# tracking system based on GNU Radio. 
#
# Copyright (C) 2013 Todd Borrowman
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import xml.dom.minidom
import time, calendar
import math
import numpy as np

class gps:
    ''' Encapsulate raw GPS data.
      
      This was written to parse data produced by the 'yellow Garmin GPS' 
      unit. It has some information/calculations that we don't need right 
      now, but may have cause to look at in the future.

      **TODO** Put this in the documentation. 
    ''' 

    def __init__(self, filename='', num_records=0):
        self.num_records = num_records
        self.time = np.zeros((self.num_records,))
        self.latitude = np.zeros((self.num_records,))
        self.longitude = np.zeros((self.num_records,))
        self.elevation = np.zeros((self.num_records,))
        self.northing = np.zeros((self.num_records,))
        self.easting = np.zeros((self.num_records,))
        self.zone = np.zeros((self.num_records,))
        if (filename != ''):
          self.read_gpx(filename)

    def read_gpx(self, filename):
        if filename.endswith('.gpx'):
            self.filename = filename
            gt = gpx_track(filename)
            for j in range(len(gt.track_points)):
                data = np.array(gt.track_points[j])
                self.num_records += data.shape[0]
                self.time = np.hstack((self.time,data[:,0]))
                self.latitude = np.hstack((self.latitude,data[:,1]))
                self.longitude = np.hstack((self.longitude,data[:,2]))
                self.elevation = np.hstack((self.elevation,data[:,3]))
                self.northing = np.hstack((self.northing,data[:,5]))
                self.easting = np.hstack((self.easting,data[:,4]))
                self.zone = np.hstack((self.zone,data[:,6]))

    def filter_by_bool(self, mask):
        new_gps_data = gps_data(np.sum(mask))
        new_gps_data.time = self.time(mask)
        new_gps_data.latitude = self.latitude(mask)
        new_gps_data.longitude = self.longitude(mask)
        new_gps_data.elevation = self.elevation(mask)
        new_gps_data.northing = self.northing(mask)
        new_gps_data.easting = self.easting(mask)
        new_gps_data.zone = self.zone(mask)
        return new_gps_data

    def write_csv(self, filename):
        with open(filename, 'w') as csvfile:
            csvfile.write("Time (seconds), Latitude (degrees), Longitude (degrees), Elevation (meters), Easting (meters), Northing (meters), Zone\n")
            for j in range(self.num_records):
                csv_str = "{0:.0f}, {1}, {2}, {3}, {4}, {5}, {6:.0f}\n".format(self.time[j], self.latitude[j], self.longitude[j], self.elevation[j], self.easting[j], self.northing[j], self.zone[j])
                csvfile.write(csv_str)

    def get_bearing(self, site_utm):
        
        if len(site_utm) == 3:
            if not np.all(site_utm[2] == self.zone):
                print "GPS UTM not all in Site UTM Zone - {0}".format(site_utm[2])
                return None, None
        bearing = np.zeros((self.num_records,2))
        for j in range(self.num_records):
            bearing[j,:] = calc_bearing_utm(site_utm, (self.easting[j], self.northing[j]))
        return bearing[:,0], bearing[:,1]

class gpx_track:

    def __init__(self,filename = "tracks.gpx"):
        self.filename = filename
        self.dom = xml.dom.minidom.parse(self.filename)
        self.read_tracks()

    def read_tracks(self):
        tracks = self.dom.getElementsByTagName("trk")
        print "Found {0} tracks.".format(len(tracks))
        self.track_points = []
        for track in tracks:
            namedom = track.getElementsByTagName("name")
            if not namedom:
                track_name = 'No Name'
            else:
                track_name = namedom[0].childNodes[0].data
            trksegs = track.getElementsByTagName("trkseg")
            print "Found {0} track segments in track {1}.".format(len(trksegs), track_name)
            for trkseg in trksegs:
                self.track_points.append([])
                namedom = trkseg.getElementsByTagName("name")
                if not namedom:
                    name = 'No Name'
                else:
                    name = namedom[0].childNodes[0].data
                    #print "Track segment: {0}".format(name)
                
                
                trkpts = trkseg.getElementsByTagName("trkpt")
                print "Found {0} track points in segment {1}.".format(len(trkpts),name)
                for trkpt in trkpts:
                    lat = trkpt.getAttribute("lat")
                    lon = trkpt.getAttribute("lon")
                    timenode = trkpt.getElementsByTagName("time")
                    timestr = timenode[0].childNodes[0].data
                    elevnode = trkpt.getElementsByTagName("ele")
                    elev = elevnode[0].childNodes[0].data

                    time_sec = calendar.timegm(time.strptime(timestr, "%Y-%m-%dT%H:%M:%SZ"))
                    utm = convert_ll_to_utm((float(lat),float(lon)))
                    self.track_points[-1].append((time_sec, float(lat), float(lon), float(elev), utm[0], utm[1], utm[2]))

                    #print "Data - Time: {} - {}, Lat: {}, Long: {}, Elev: {}".format(timestr,time_sec,lat,lon,elev)
                    #break

def calc_bearing(origin,destination):
        #Vincenty formula for distance and bearing on WGS-84 spheriod
        #http://www.movable-type.co.uk/scripts/latlong-vincenty.html
        #input is tuple (lat,long)

        a = 6378137
        b = 6356752.314245
        f = 1/298.257223563
        phi1 = origin[0]*math.pi/180.0
        phi2 = destination[0]*math.pi/180.0
        L = (destination[1] - origin[1])*math.pi/180.0
        U1 = math.atan((1-f)*math.tan(phi1))
        cU1 = math.cos(U1)
        sU1 = math.sin(U1)
        U2 = math.atan((1-f)*math.tan(phi2))
        cU2 = math.cos(U2)
        sU2 = math.sin(U2)
        lamb = L
        dlamb = 1
        while dlamb > 10**-12:
            slamb = math.sin(lamb)
            clamb = math.cos(lamb)
            sin_sigma = math.sqrt(cU2*slamb*cU2*slamb + (cU1*sU2 - sU1*cU2*clamb)*(cU1*sU2 - sU1*cU2*clamb))
            if sin_sigma == 0: return (0,0,0)
            cos_sigma = sU1*sU2 + cU1*cU2*clamb
            sigma = math.atan2(sin_sigma, cos_sigma)
            sin_alpha = cU1*cU2*slamb/sin_sigma
            cos2_alpha = 1 - sin_alpha*sin_alpha
            if cos2_alpha == 0:
                cos_2sigmam = 0
            else:
                cos_2sigmam = cos_sigma - 2*sU1*sU2/cos2_alpha
            C = f/16*cos2_alpha*(4+f*(4-3*cos2_alpha))
            prev_lamb = lamb
            lamb = L + (1-C)*f*sin_alpha*(sigma+C*sin_sigma*(cos_2sigmam+C*cos_sigma*(-1+2*cos_2sigmam*cos_2sigmam)))
            dlamb = lamb - prev_lamb

        usq = cos2_alpha*(a*a-b*b)/(b*b)
        A = 1+usq/16384*(4096+usq*(-768+usq*(320-175*usq)))
        B = usq/1024*(256+usq*(-128+usq*(74-47*usq)))
        delta_sigma = B*sin_sigma*(cos_2sigmam+B/4*(cos_sigma*(-1+2*cos_2sigmam*cos_2sigmam) - B/6*cos_2sigmam*(-3+4*sin_sigma*sin_sigma)*(-3+4*cos_2sigmam*cos_2sigmam)))
        s = b*A*(sigma - delta_sigma)
        alpha1 = math.atan2(cU2*math.sin(lamb),cU1*sU2-sU1*cU2*math.cos(lamb))
        alpha2 = math.atan2(cU1*sU2,-sU1*cU2+cU1*sU2*math.cos(lamb))
        
        return (s,alpha1*180/math.pi,alpha2*180/math.pi)

def convert_ll_to_utm(ll_tuple):
    #converts (latitude, longitude) to (Easting, Northing, Zone) using WGS84
    # or (latitude, longitude, elevation) to (Easting, Northing, elevation, Zone)
    #reference http://www.uwgb.edu/dutchs/usefuldata/utmformulas.htm

    lat = ll_tuple[0]*math.pi/180.0
    lon = ll_tuple[1]*math.pi/180.0
    
    clat = math.cos(lat)
    slat = math.sin(lat)
    tlat = math.tan(lat)
    zone = ll_tuple[1]//6 + 31
    lon0 = ((ll_tuple[1]//6)*6 + 3.0)*math.pi/180.0
    k0 = 0.9996
    a = 6378137.0
    b = 6356752.3142
    e2 = 1-b**2/a**2
    eprime2 = e2/(1-e2)
    n = (a-b)/(a+b)
    rho = a*(1-e2)/(1-e2*slat**2)**(1.5)
    nu = a/(1-e2*slat**2)**(0.5)
    p = lon - lon0
    
    Aprime = a*(1-n+(5*n*n/4)*(1-n)+(81*n**4/64)*(1-n))
    Bprime = (3*a*n/2)*(1-n-(7*n*n/8)*(1-n)+55*n**4/64)
    Cprime = (15*a*n*n/16)*(1-n+(3*n*n/4)*(1-n))
    Dprime = (35*a*n**3/48)*(1-n+11*n*n/16)
    Eprime = (315*a*n**4/51)*(1-n)
    S = Aprime*lat-Bprime*math.sin(2*lat)+Cprime*math.sin(4*lat)-Dprime*math.sin(6*lat)+Eprime*math.sin(8*lat)

    K1 = S*k0
    K2 = k0*nu*slat*clat/2
    K3 = (k0*nu*slat*clat**3/24)*(5-tlat**2+9*eprime2*clat**2+4*eprime2**2*clat**4)
    K4 = k0*nu*clat
    K5 = (k0*nu*clat**3/6)*(1-tlat**2+eprime2*clat**2)

    northing = K1 + K2*p**2 + K3*p**4
    easting = K4*p + K5*p**3 + 500000

    if len(ll_tuple) == 3:
        loc_utm = (easting, northing, ll_tuple[2], zone)
    else:
        loc_utm = (easting, northing, zone)

    return loc_utm

def calc_bearing_utm(origin,destination):

    if len(origin) > 2 and len(destination) > 2:
        if not (origin[-1] == destination[-1]):
            print "Not in same zone.  Use calc_bearing with lat long"
            return (0,0)
    bearing = math.atan2(destination[0]-origin[0],destination[1]-origin[1])*180.0/math.pi
    distance = math.sqrt((destination[0]-origin[0])**2+(destination[1]-origin[1])**2)
    return (bearing, distance)

def calc_bearing_ll_to_utm(origin,destination):
    return calc_bearing_utm(convert_ll_to_utm(origin),convert_ll_to_utm(destination))

class gpx_waypoints:

    def __init__(self,filename = "newwaypoints.gpx"):
        self.filename = filename
        self.dom = xml.dom.minidom.parse(self.filename)
        self.read_waypoints()

    def read_waypoints(self):
        wpts = self.dom.getElementsByTagName("wpt")
        self.names = []
        self.times = []
        self.lats = []
        self.longs = []
        self.elevs = []
        for wpt in wpts:
            namenode = wpt.getElementsByTagName("name")
            self.names.append(namenode[0].childNodes[0].data)
            timenode = wpt.getElementsByTagName("time")
            self.times.append(timenode[0].childNodes[0].data)
            elevnode = wpt.getElementsByTagName("ele")
            self.elevs.append(float(elevnode[0].childNodes[0].data))
            self.lats.append(float(wpt.getAttribute("lat")))
            self.longs.append(float(wpt.getAttribute("lon")))
            print "Waypoint: {0} at Time: {1}".format(self.names[-1],self.times[-1])

    def get_waypoint(self,wpt_name):
        wpts = self.dom.getElementsByTagName("wpt")
        loc = (0,0)
        for wpt in wpts:
            namenode = wpt.getElementsByTagName("name")
            name = namenode[0].childNodes[0].data
            if name == wpt_name:
                elevnode = wpt.getElementsByTagName("ele")
                elev = elevnode[0].childNodes[0].data
                loc = (float(wpt.getAttribute("lat")),float(wpt.getAttribute("lon")),float(elev))
        return loc

    def write_csv(self, csv_filename):

        with open(csv_filename,'w') as csvfile:
            csvfile.write("Name, DateTime, Latitude, Longitude, Elevation, Northing, Easting, Zone\n")
            for j in range(len(self.names)):
                utm_coords = convert_ll_to_utm((self.lats[j],self.longs[j]))
                csvfile.write("{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}\n".format(self.names[j],
                               self.times[j],
                               self.lats[j],
                               self.longs[j],
                               self.elevs[j],
                               utm_coords[1],
                               utm_coords[0],
                               utm_coords[2]))


if __name__ == "__main__":

    gw = gpx_waypoints('./gps/site_waypoints.gpx')
    coords1 = gw.get_waypoint('Siteone')
    coords2 = gw.get_waypoint('Sitetwo')
    print "UTMs 1:", convert_ll_to_utm(coords1)
    print "UTMs 2:", convert_ll_to_utm(coords2)
    print "UTM Bearing:", calc_bearing_utm(convert_ll_to_utm(coords1),convert_ll_to_utm(coords2))
    print "LL Bearing:", calc_bearing(coords1,coords2)



    #gf = gpx_track("/data/Quail_Ridge/gps/23102012test.gpx")
    #gf.read_tracks()
    #gw = gpx_waypoints()
    #gw.read_waypoints()
    #rmg_loc = gw.get_waypoint("QRRMG1")

    #print calc_bearing((47.76548, 8.99827),rmg_loc)

#    with open("bearing_QRRMG1_20121023.txt",'w') as bfile:
#        bfile.write("Time(seconds past epoch), Latitude(degrees), Longitude(degrees), Bearing(degrees), Distance(meters), Elevation(meters)\n")
#        for j in gf.track_points:
#            for k in j:
#                bearing = calc_bearing(rmg_loc,k[1:3])
#                bfile.write("{0}, {1}, {2}, {3}, {4}, {5}\n".format(k[0],k[1],k[2],bearing[1],bearing[0],k[3]))



