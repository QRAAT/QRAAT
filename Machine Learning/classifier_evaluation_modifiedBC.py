import qraatSignal
import MySQLdb
import numpy as np
import time
import math

def uniformDist(x, mean, var, dataType, startTime,
                validation, deploymentID, siteID, manOrLik):
  """
      Calculate the log probability of mixed probability 
      distrubtion of discrete variables.
  """
  
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  cur = db_con.cursor()
  cur.execute("""SELECT probability
                 FROM probability_of_discrete_data%s
                 WHERE start_time = %s
                 AND validation = %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND data_type = '%s'
                 AND data_value = %s;
              """%(manOrLik, startTime, validation,
                   deploymentID, siteID, dataType, x))
  prob = 0
  for row in cur.fetchall():
    prob = row[0]
  if (prob == 0):
    return (- (x - mean)**2/(2*var) \
           - 0.5*np.log(2*np.pi*var))
  else:
    return np.log(prob)

def normalDist(x, mean, var):
  """
     Calculate the log probability of normal distrubtion.
  """

  if (var != 0):
    return -(x - mean)**2/(2*var) - 0.5*np.log(2*np.pi*var)
  else:
    return 0

def modifiedBC(deploymentID, siteID, start_time,
               validation, estData, manOrLik):
  """
     Classify data with modified bayes classifier.
  """
  db_con = MySQLdb.connect(user = "root", db = "qraat")

  #Get mean and variance for each variable for each class.
  cur = db_con.cursor()
  cur.execute("""SELECT *
                 FROM est_mean_and_var%s
                 WHERE start_time = %s
                 AND validation = %s
                 AND deploymentID = %s
                 AND siteID = %s;
              """%(manOrLik, start_time, validation,
                   deploymentID, siteID))
  for row in cur.fetchall():
    if (row[24] == 1):
      if (row[5] != 0):
          
        #Calculate the likelihood of this observation being a pulse
        goodLikelihood = np.log(row[5]) \
                         + uniformDist(estData['band3'], row[6], row[7],
                                       'band3', start_time, validation,
                                       deploymentID, siteID, manOrLik) \
                         + uniformDist(estData['band10'], row[8], row[9],
                                       'band10', start_time, validation,
                                       deploymentID, siteID, manOrLik) \
                         + uniformDist(estData['frequency'], row[10], row[11],
                                       'frequency', start_time, validation,
                                       deploymentID, siteID, manOrLik) \
                         + normalDist(estData['ec'], row[12], row[13]) \
                         + normalDist(estData['tnp'], row[14], row[15]) \
                         + normalDist(estData['edsp'], row[16], row[17]) \
                         + normalDist(estData['fdsp'], row[18], row[19]) \
                         + normalDist(estData['edsnr'], row[20], row[21]) \
                         + normalDist(estData['fdsnr'], row[22], row[23])
      else:
        goodLikelihood = -float('inf')
    else:
      if (row[5] != 0):
          
        #Calculate the likelihoood of this observation being a noise
        badLikelihood = np.log(row[5]) \
                        + normalDist(estData['band3'], row[6], row[7]) \
                         + normalDist(estData['band10'], row[8], row[9]) \
                         + normalDist(estData['frequency'], row[10], row[11]) \
                         + normalDist(estData['ec'], row[12], row[13]) \
                         + normalDist(estData['tnp'], row[14], row[15]) \
                         + normalDist(estData['edsp'], row[16], row[17]) \
                         + normalDist(estData['fdsp'], row[18], row[19]) \
                         + normalDist(estData['edsnr'], row[20], row[21]) \
                         + normalDist(estData['fdsnr'], row[22], row[23])
      else:
        badLikelihood = -float('inf')
    
  #Return the class with higher likelihood.
  if (goodLikelihood < badLikelihood):
    return 0
  else:
    return 1

def evaluation(deploymentID, start_time,
               end_time, sites, validation, manOrLik):
  """
     Find TP, TN, FP, and FN.
  """
  
  estScoreBound = 5
  falsePositive_dep = 0
  falseNegative_dep = 0
  truePositive_dep = 0
  trueNegative_dep = 0

  db_con = MySQLdb.connect(user="root", db="qraat")
  for i in sites:
    truePositive = 0
    trueNegative = 0
    falsePositive = 0
    falseNegative = 0
    
    cur = db_con.cursor()
    cur.execute("""SELECT isPulse, band3, band10, frequency,
                   ec, tnp, edsp, fdsp, edsnr, fdsnr
                   FROM est INNER JOIN est_class%s
                   ON ID = est_class%s.estID
                   INNER JOIN estscore2
                   ON ID = estscore2.estID
                   WHERE timestamp > %s
                   AND timestamp < %s
                   AND deploymentID = %s
                   AND siteID = %s
                   AND setNum = %s;
                """%(manOrLik, manOrLik, start_time, end_time,
                     deploymentID, i, validation))
    for row in cur.fetchall():
      estData = {'band3':row[1], 'band10':row[2],
                 'frequency':row[3], 'ec':row[4], 'tnp':row[5],
                 'edsp':row[6], 'fdsp':row[7],
                 'edsnr':row[8], 'fdsnr':row[9]}
      
      #Classify data
      isPulse = modifiedBC(deploymentID, i, start_time,
                           validation, estData, manOrLik)

      #Determine whether the classification results are correct or not
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
          
    falsePositive_dep += falsePositive
    falseNegative_dep += falseNegative
    truePositive_dep += truePositive
    trueNegative_dep += trueNegative
  return [truePositive_dep, trueNegative_dep,
          falsePositive_dep, falseNegative_dep]

  
def insertResults(depID, validation):
  """
     Gather results from evaluation functions, stores them
     to the database, and print the results.
  """
  db_con = MySQLdb.connect(user="root", db="qraat")
  start_time = {57:1382252400,
                60:1383012615,
                61:1396725597,
                62:1396725597}
  end_time = {57:1385366400,
              60:1384222215,
              61:1396732326,
              62:1396732326}
  sites = {57:[2,3,5,6],
           60:[1,2,3,4,5,6,8],
           61:[1,2,3,4,5,6,8],
           62:[1,2,3,4,5,6,8]}
  
  #Evaluate both manual labeling and likelihood labeling
  evalMan = evaluation(depID, start_time[depID], end_time[depID],
                       sites[depID], validation, '')
  evalLik = evaluation(depID, start_time[depID], end_time[depID],
                       sites[depID], validation, '2')

  #Additional evaluation for deployment 61 and 62
  if ((depID == 61) | (depID == 62)):
    start_time = 1391276584
    end_time = 1391285374
    sites = [1,3,4,5,6,8]
    tmpEvalMan = evaluation(depID, start_time, end_time,
                            sites, validation, '')
    tmpEvalLik = evaluation(depID, start_time, end_time,
                            sites, validation, '2')
    for i in range(4):
      evalMan[i] += tmpEvalMan[i]
      evalLik[i] += tmpEvalLik[i]

  #Export data into database
  cur = db_con.cursor()
  cur.execute("""INSERT INTO classifier_performance
                 (deploymentID, validation, TP, TN,
                 FP, FN, total_records, classifier_type)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'modified BC')
              """%(depID, validation, evalMan[0], evalMan[1],
                   evalMan[2], evalMan[3], sum(evalMan)))
  cur2 = db_con.cursor()
  cur2.execute("""INSERT INTO classifier_performance2
                  (deploymentID, validation, TP, TN,
                  FP, FN, total_records, classifier_type)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, 'modified BC')
               """%(depID, validation, evalLik[0], evalLik[1],
                    evalLik[2], evalLik[3], sum(evalLik)))

  #Print results
  print depID, validation
  print 'Manual:'
  print 'False Positive Rate: %s'%(float(evalMan[2])/(evalMan[2] + evalMan[1]))
  print 'False Nagative Rate: %s'%(float(evalMan[3])/(evalMan[3] + evalMan[0]))
  print 'Overall Error Rate: %s'%(float(evalMan[2] + evalMan[3])/(sum(evalMan)))
  print 'Likelihood:'
  print 'False Positive Rate: %s'%(float(evalLik[2])/(evalLik[2] + evalLik[1]))
  print 'False Nagative Rate: %s'%(float(evalLik[3])/(evalLik[3] + evalLik[0]))
  print 'Overall Error Rate: %s'%(float(evalLik[2] + evalLik[3])/(sum(evalLik)))

def main():
  """
     This program should evaluate all combinations
     of deployment and site with modified bayes classifier.
     It will evulate 10 times on each different
     tranining set and validation set. It will also
     evaluate on both manual labeling and likelihood labeling.
  """
  
  #Loop through each validation and deployment
  initTime = time.time()
  deploymentIDArray = [57, 60, 61, 62]
  for i in range(10):
    for j in deploymentIDArray:
      insertResults(j, i)

  print time.time() - initTime
  
if __name__ == '__main__':
  main()
