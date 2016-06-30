import numpy as np
from PIL import Image
from geographiclib.geodesic import Geodesic

class elevation_model:

  def __init__(self, tif, tfw):
    im = Image.open(tif)
    self.elevation_array = np.array(im)
    with open(tfw) as f:
      self.scale_data = np.loadtxt(f, dtype=float, delimiter='\n')
    self.max_x = self.elevation_array.shape[0]
    self.max_y = self.elevation_array.shape[1]
    self.max_lat, self.min_lon = self.index_to_latlon(0,0)
    self.min_lat, self.max_lon = self.index_to_latlon(self.max_x, self.max_y)

  def latlon_to_index(self, lat, lon):
    x_index = (self.scale_data[2]*(lon-self.scale_data[4])+self.scale_data[0]*(lat-self.scale_data[5]))/(self.scale_data[0]*self.scale_data[3]+self.scale_data[1]*self.scale_data[2])
    y_index = (self.scale_data[3]*(lon-self.scale_data[4])+self.scale_data[1]*(lat-self.scale_data[5]))/(self.scale_data[0]*self.scale_data[3]+self.scale_data[1]*self.scale_data[2])
    return x_index, y_index

  def index_to_latlon(self, x_index, y_index):
    lat = self.scale_data[2]*y_index+self.scale_data[3]*x_index+self.scale_data[5]
    lon = self.scale_data[0]*y_index+self.scale_data[1]*x_index+self.scale_data[4]
    return lat, lon

  def get_elevation(self, lat, lon):
    #closest point on grid
    x,y = self.latlon_to_index(lat,lon)
    int_x = int(round(x))
    if int_x < 0:
      int_x = 0
    elif int_x >= self.elevation_array.shape[0]:
      int_x = self.elevation_array.shape[0]-1
    int_y = int(round(y))
    if int_y < 0:
      int_y = 0
    elif int_y >= self.elevation_array.shape[1]:
      int_y = self.elevation_array.shape[1]-1
    return self.elevation_array[int_x,int_y]

class line_of_sight():

  def __init__(self, em, lat, lon, elevation=None):
    self.em = em
    self.lat = lat
    self.lon = lon
    if elevation is None:
      self.elevation = self.em.get_elevation(self.lat, self.lon)
    else:
      self.elevation = elevation
    self.elevation_angle = None

  def calc_elevation_angle_array(self):
    self.elevation_angle = np.zeros(self.em.elevation_array.shape)
    for j in range(self.elevation_angle.shape[0]):
      for k in range(self.elevation_angle.shape[1]):
        to_lat,to_lon = self.em.index_to_latlon(j, k)
        self.elevation_angle[j,k] = calc_elevation_angle(to_lat, to_lon, elevation=self.em.elevation_array[j,k])


  def calc_elevation_angle(self, to_lat, to_lon, dist=None, elevation=None):
    if dist is None:
      g = Geodesic.WGS84.Inverse(self.lat, self.lon, to_lat, to_lon)
      dist = g['s12']
    if elevation is None:
      elevation = self.em.get_elevation(to_lat,to_lon)
    return np.arctan2(elevation-self.elevation, dist)

  def get_elevation_angle(self, lat, lon, dist=None, elevation=None):
    #closest point on grid
    x,y = self.em.latlon_to_index(lat,lon)
    int_x = int(round(x))
    if int_x < 0:
      int_x = 0
    elif int_x >= self.em.max_x:
      int_x = self.em.max_x-1
    int_y = int(round(y))
    if int_y < 0:
      int_y = 0
    elif int_y >= self.em.max_y:
      int_y = self.em.max_y-1
    if elevation is None:
      if self.elevation_angle:
        ea = self.elevation_angle[int_x,int_y]
      else:
        ea = self.calc_elevation_angle(lat, lon, dist, self.em.elevation_array[int_x,int_y])
    else:
      ea = self.calc_elevation_angle(lat, lon, dist, elevation)
    return ea

  def can_see(self, lat, lon, elev=None):
    step_size = 10
    g = Geodesic.WGS84.Inverse(self.lat, self.lon, lat, lon)
    geo_line = Geodesic.WGS84.Line(self.lat, self.lon, g['azi1'])
    ea = self.get_elevation_angle(lat,lon, g['s12'], elev)
    dist = g['s12']-step_size
    can_see_bool = True
    while dist > 0:
      new_loc = geo_line.Position(dist)
      test_ea = self.get_elevation_angle(new_loc['lat2'],new_loc['lon2'], dist)
      if test_ea > ea:
        can_see_bool = False
        break
      dist -= step_size
    return can_see_bool

if __name__ == '__main__':
  em = elevation_model('/home/todd/qraat_workspace/QR_topo/50245025.tif', '/home/todd/qraat_workspace/QR_topo/50245025.tfw')
  los = line_of_sight(em, 38.495196, -122.151395)
  print los.can_see(38.45,-122.15,-100)

