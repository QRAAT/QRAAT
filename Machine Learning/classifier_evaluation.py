import qraatSignal
import MySQLdb
import numpy as np
import time
import math

def uniformDist(x, mean, var, dataType, startTime,
                endTime, deploymentID, siteID):
  db_con = MySQLdb.connect(user = "root", db = "qraat")

  cur = db_con.cursor()
  cur.execute("""SELECT probability
                 FROM probability_of_discrete_data
                 WHERE start_time = %s
                 AND end_time = %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND data_type = '%s'
                 AND data_value = %s;
              """%(startTime, endTime, deploymentID,
                   siteID, dataType, x))
  prob = 0
  for row in cur.fetchall():
    prob = row[0]
  if (prob == 0):
    return (- (x - mean)**2/(2*var) \
           - 0.5*np.log(2*np.pi*var))
  else:
    return np.log(prob)


def modifiedBC(deploymentID, siteID, startTime, endTime, estData):
  db_con = MySQLdb.connect(user = "root", db = "qraat")

  cur = db_con.cursor()
  cur.execute("""SELECT *
                 FROM est_mean_and_var
                 WHERE start_time = %s
                 AND end_time = %s
                 AND deploymentID = %s
                 AND siteID = %s;
              """%(startTime, endTime, deploymentID, siteID))
  for row in cur.fetchall():
    if (row[24] == 1):
      if (row[5] != 0):
        goodLikelihood = np.log(row[5]) \
                         + uniformDist(estData['band3'], row[6], row[7],
                                       'band3', startTime, endTime,
                                       deploymentID, siteID) \
                         + uniformDist(estData['band10'], row[8], row[9],
                                       'band10', startTime, endTime,
                                       deploymentID, siteID) \
                         + uniformDist(estData['frequency'], row[10], row[11],
                                       'frequency', startTime, endTime,
                                       deploymentID, siteID) \
                         - (estData['ec'] - row[12])**2/(2*row[13]) \
                         - 0.5*np.log(2*np.pi*row[13]) \
                         - (estData['tnp'] - row[14])**2/(2*row[15]) \
                         - 0.5*np.log(2*np.pi*row[15]) \
                         - (estData['edsp'] - row[16])**2/(2*row[17]) \
                         - 0.5*np.log(2*np.pi*row[17]) \
                         - (estData['fdsp'] - row[18])**2/(2*row[19]) \
                         - 0.5*np.log(2*np.pi*row[19]) \
                         - (estData['edsnr'] - row[20])**2/(2*row[21]) \
                         - 0.5*np.log(2*np.pi*row[21]) \
                         - (estData['fdsnr'] - row[22])**2/(2*row[23]) \
                         - 0.5*np.log(2*np.pi*row[23])
      else:
        goodLikelihood = -float('inf')
    else:
      if (row[5] != 0):
        badLikelihood = np.log(row[5]) \
                        - (estData['band3'] - row[6])**2/(2*row[7]) \
                        - 0.5*np.log(2*np.pi*row[7]) \
                        - (estData['band10'] - row[8])**2/(2*row[9]) \
                        - 0.5*np.log(2*np.pi*row[9]) \
                        - (estData['frequency'] - row[10])**2/(2*row[11]) \
                        - 0.5*np.log(2*np.pi*row[11]) \
                        - (estData['ec'] - row[12])**2/(2*row[13]) \
                        - 0.5*np.log(2*np.pi*row[13]) \
                        - (estData['tnp'] - row[14])**2/(2*row[15]) \
                        - 0.5*np.log(2*np.pi*row[15]) \
                        - (estData['edsp'] - row[16])**2/(2*row[17]) \
                        - 0.5*np.log(2*np.pi*row[17]) \
                        - (estData['fdsp'] - row[18])**2/(2*row[19]) \
                        - 0.5*np.log(2*np.pi*row[19]) \
                        - (estData['edsnr'] - row[20])**2/(2*row[21]) \
                        - 0.5*np.log(2*np.pi*row[21]) \
                        - (estData['fdsnr'] - row[22])**2/(2*row[23]) \
                        - 0.5*np.log(2*np.pi*row[23])
      else:
        badLikelihood = -float('inf')
    
  if (goodLikelihood < badLikelihood):
    return 0
  else:
    return 1

def estScoreFilter(estScore, estScoreBound):
  if (estScore > estScoreBound):
    return 0
  else:
    return 1
  
  
def naiveBayes(deploymentID, siteID, startTime, endTime, estData):
  db_con = MySQLdb.connect(user = "root", db = "qraat")

  cur = db_con.cursor()
  cur.execute("""SELECT *
                 FROM est_mean_and_var
                 WHERE start_time = %s
                 AND end_time = %s
                 AND deploymentID = %s
                 AND siteID = %s;
              """%(startTime, endTime, deploymentID, siteID))
  for row in cur.fetchall():
    if (row[24] == 1):
      if (row[5] != 0):
        goodLikelihood = np.log(row[5]) \
                         - (estData['band3'] - row[6])**2/(2*row[7]) \
                         - 0.5*np.log(2*np.pi*row[7]) \
                         - (estData['band10'] - row[8])**2/(2*row[9]) \
                         - 0.5*np.log(2*np.pi*row[9]) \
                         - (estData['frequency'] - row[10])**2/(2*row[11]) \
                         - 0.5*np.log(2*np.pi*row[11]) \
                         - (estData['ec'] - row[12])**2/(2*row[13]) \
                         - 0.5*np.log(2*np.pi*row[13]) \
                         - (estData['tnp'] - row[14])**2/(2*row[15]) \
                         - 0.5*np.log(2*np.pi*row[15]) \
                         - (estData['edsp'] - row[16])**2/(2*row[17]) \
                         - 0.5*np.log(2*np.pi*row[17]) \
                         - (estData['fdsp'] - row[18])**2/(2*row[19]) \
                         - 0.5*np.log(2*np.pi*row[19]) \
                         - (estData['edsnr'] - row[20])**2/(2*row[21]) \
                         - 0.5*np.log(2*np.pi*row[21]) \
                         - (estData['fdsnr'] - row[22])**2/(2*row[23]) \
                         - 0.5*np.log(2*np.pi*row[23])
      else:
        goodLikelihood = -float('inf')
    else:
      if (row[5] != 0):
        badLikelihood = np.log(row[5]) \
                        - (estData['band3'] - row[6])**2/(2*row[7]) \
                        - 0.5*np.log(2*np.pi*row[7]) \
                        - (estData['band10'] - row[8])**2/(2*row[9]) \
                        - 0.5*np.log(2*np.pi*row[9]) \
                        - (estData['frequency'] - row[10])**2/(2*row[11]) \
                        - 0.5*np.log(2*np.pi*row[11]) \
                        - (estData['ec'] - row[12])**2/(2*row[13]) \
                        - 0.5*np.log(2*np.pi*row[13]) \
                        - (estData['tnp'] - row[14])**2/(2*row[15]) \
                        - 0.5*np.log(2*np.pi*row[15]) \
                        - (estData['edsp'] - row[16])**2/(2*row[17]) \
                        - 0.5*np.log(2*np.pi*row[17]) \
                        - (estData['fdsp'] - row[18])**2/(2*row[19]) \
                        - 0.5*np.log(2*np.pi*row[19]) \
                        - (estData['edsnr'] - row[20])**2/(2*row[21]) \
                        - 0.5*np.log(2*np.pi*row[21]) \
                        - (estData['fdsnr'] - row[22])**2/(2*row[23]) \
                        - 0.5*np.log(2*np.pi*row[23])
      else:
        badLikelihood = -float('inf')
    
  if (goodLikelihood < badLikelihood):
    return 0
  else:
    return 1

def bandwidthFilter(band3, band10, band3Bound, band10Bound):
  if ((band3 < band3Bound)&(band10 < band10Bound)):
    return 1
  else:
    return 0

def main():
##  deploymentID = 57
##  start_time = 1382252400
##  end_time = 1385366400
##  sites = [2,3,5,6]

##  deploymentID = 60
##  start_time = 1383012615
##  end_time = 1383012615 + 3600*24*14
##  sites = [1,2,3,4,5,6,8]

##  deploymentID = 61
##  deploymentID = 62
  
##  start_time = 1396725597
##  end_time = 1396732326
##  sites = [1,2,3,4,5,6,8]

##  start_time = 1391276584
##  end_time = 1391285374
##  sites = [1,3,4,5,6,8]
  
##  band3Bound = 450
##  band10Bound = 900
##  classifierType = '\'bandwidth filter with band3 < %s and band10 < %s\''%(band3Bound, band10Bound)
##  classifierType = '\'Naive Bayes Classifier\''
##  estScoreBound = 5
##  classifierType = '\'estScoreFilter\''
  classifierType = '\'modified BC\''

  falsePositive_dep = 0
  falseNegative_dep = 0
  truePositive_dep = 0 
  trueNegative_dep = 0
  totalRecords_dep = 0

  db_con = MySQLdb.connect(user="root", db="qraat")
  for i in sites:
    truePositive = 0
    trueNegative = 0
    falsePositive = 0
    falseNegative = 0
    totalRecords = 0
    
    cur = db_con.cursor()
    cur.execute("""SELECT isPulse, band3, band10,
                   frequency, ec, tnp, edsp, fdsp, edsnr,
                   fdsnr, total_score
                   FROM est INNER JOIN est_class
                   ON ID = est_class.estID
                   INNER JOIN estscore2
                   ON ID = estscore2.estID
                   WHERE timestamp > %s
                   AND timestamp < %s
                   AND deploymentID = %s
                   AND siteID = %s
                   AND setNum > 7;
                """%(start_time, end_time, deploymentID, i))
    for row in cur.fetchall():
      totalRecords += 1
      estData = {'band3':row[1], 'band10':row[2],
                 'frequency':row[3], 'ec':row[4], 'tnp':row[5],
                 'edsp':row[6], 'fdsp':row[7],
                 'edsnr':row[8], 'fdsnr':row[9]}
      
##      isPulse = bandwidthFilter(row[1], row[2], band3Bound, band10Bound)
##      isPulse = naiveBayes(deploymentID, i, start_time, end_time, estData)
##      isPulse = estScoreFilter(row[10], estScoreBound)
      isPulse = modifiedBC(deploymentID, i, start_time, end_time, estData)

      if (row[0] == 1):
        if (isPulse == 1):
          truePositive += 1
        else:
          falseNegative += 1
      else:
        if (isPulse == 1):
          falsePositive += 1
        else:
          trueNegative += 1
      
##    print i, falsePositive, falseNegative, totalRecords
    falsePositive_dep += falsePositive
    falseNegative_dep += falseNegative
    truePositive_dep += truePositive
    trueNegative_dep += trueNegative
    totalRecords_dep +=totalRecords
##    print float(falsePositive)/totalRecords, float(falseNegative)/totalRecords

    cur2 = db_con.cursor()
    cur2.execute("""INSERT INTO classifier_performance
                    (deploymentID, siteID, start_time, end_time,
                    true_positive, true_negative, false_positive,
                    false_negative, total_records, classifier_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                 """%(deploymentID, i, start_time, end_time,
                      truePositive, trueNegative, falsePositive,
                      falseNegative, totalRecords, classifierType))

  print falsePositive_dep, (falsePositive_dep + trueNegative_dep), falseNegative_dep, (falseNegative_dep + truePositive_dep), totalRecords_dep
  print 'False Positive Rate: %s'%(float(falsePositive_dep)/(falsePositive_dep + trueNegative_dep))
  print 'False Nagative Rate: %s'%(float(falseNegative_dep)/(falseNegative_dep + truePositive_dep))
  print 'Overall Error Rate: %s'%(float(falsePositive_dep + falseNegative_dep)/(totalRecords_dep))
if __name__ == '__main__':
  main()
