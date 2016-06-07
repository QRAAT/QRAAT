import qraatSignal
import MySQLdb
import time

def spectrum(start_time, end_time, siteID, deployment_id):
  cal_id=11

  db_con = MySQLdb.connect(
                       user="root",
                       db="qraat") # name of the data base
  cur = db_con.cursor()
  
  sv = qraatSignal.SteeringVectors(db_con, cal_id, include=siteID)
  sig = qraatSignal.Signal(db_con, deployment_id, start_time, end_time,
                           score_threshold = 0)
  method = qraatSignal.Signal.Bartlet
  if len(sig) > 0: 
    bearing_spectrum = {} # Compute bearing likelihood distributions.  
    for site_id in sig.get_site_ids().intersection(sv.get_site_ids()):
      (bearing_spectrum[site_id], obj) = method(sig[site_id], sv)

    outputSites = sig.get_site_ids().intersection(sv.get_site_ids())

    return bearing_spectrum, sig
  else:
    return {},sig

def bearingExport(deploymentID, start_time, end_time, siteIDs, normalized):
  for i in range(start_time, end_time+1, 30):
    if i%5000==0:
      print float(i - start_time)/1200000
    bearingDict, sig = spectrum(i, i+30, siteIDs, deploymentID)
    for j in bearingDict:
      fileName = 'deployment %s - site %s.txt'%(deploymentID, j)
      f = open(fileName,'a')
      for k in range(len(bearingDict[j])):
        if normalized:
          bearingDict[j][k] /= sum(bearingDict[j][k])
        c = str(sig[j].t[k])+','+','.join([str(bearingDict[j][k][l]) for l in range(360)])+'\n'
        f.write(c)
      f.close()
      
def main():
  normalized = 0
  
  initTime = time.time()
  start_time = {142:1461884300,
                116:1435782759}
  end_time = {142:1461886955,
              116:1436713781}
  sites = {142:[2,11,12,13],
           116:[2,11,12,13]}
  
  for i in [142, 116]:
    bearingExport(i, start_time[i], end_time[i], sites[i], normalized)

  print 'Took %s seconds.'%(time.time()-initTime)
  
  
if __name__ == '__main__':
  main()
