# Combine siteN.csv's into one big CSV file. 

import qraat

dep_id = 105
sites = [1, 2, 3, 4, 5, 8]

fd = open('test-data.csv', 'w')
fd.write('dep_id,site_id,est_id,t,power,good\n')

for site_id in sites:

  points = qraat.csv.csv('site%d.csv' % site_id)
  for point in points:
    fd.write('%d,%d,%s,%s,%s,%s\n' % (site_id, site_id,
       point.est_id, point.t, point.power, point.good))

fd.close()
