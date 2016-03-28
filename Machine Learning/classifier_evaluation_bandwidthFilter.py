import qraatSignal
import MySQLdb
import numpy as np
import time
import math

def bandwidthFilter(band3, band10, band3Bound, band10Bound):
  """
     classfy pulse if both band3 and band10 and under the threshold, noise vice versa
  """
  if ((band3 < band3Bound)&(band10 < band10Bound)):
    return 1
  else:
    return 0


def likelihoodLabelingEvaluation(deploymentID, start_time, end_time,
                                 sites, validation):
  """
     Find the TP, TN, FP, and FN for the deployment and time for likelihood labeling.
  """
  
  band3Bound = 450
  band10Bound = 900
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
    cur.execute("""SELECT isPulse, band3, band10
                   FROM est INNER JOIN est_class2
                   ON ID = est_class2.estID
                   WHERE timestamp > %s
                   AND timestamp < %s
                   AND deploymentID = %s
                   AND siteID = %s
                   AND setNum = %s;
                """%(start_time, end_time, deploymentID, i, validation))
    for row in cur.fetchall():
      isPulse = bandwidthFilter(row[1], row[2], band3Bound, band10Bound)

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

def manualLabelingEvaluation(deploymentID, start_time, end_time,
                               sites, validation):
  """
     Find the TP, TN, FP, and FN for the deployment and time for manual labeling.
  """
  
  band3Bound = 450
  band10Bound = 900
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
    cur.execute("""SELECT isPulse, band3, band10
                   FROM est INNER JOIN est_class
                   ON ID = est_class.estID
                   WHERE timestamp > %s
                   AND timestamp < %s
                   AND deploymentID = %s
                   AND siteID = %s
                   AND setNum = %s;
                """%(start_time, end_time, deploymentID, i, validation))
    for row in cur.fetchall():
      isPulse = bandwidthFilter(row[1], row[2], band3Bound, band10Bound)

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

  
def evaluation(depID, validation):
  """
      Go through each combinations of site and evaluate bandwidth
      filter with each of manual labeling and likelihood labeling.
      The evaluation result is stored in the classifier_performance
      table. It also prints the result.
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
  
  evalMan = manualLabelingEvaluation(depID, start_time[depID],
                                     end_time[depID], sites[depID],
                                     validation)
  evalLik = likelihoodLabelingEvaluation(depID, start_time[depID],
                                         end_time[depID], sites[depID],
                                         validation)
  
  if ((depID == 61) | (depID == 62)):
    start_time = 1391276584
    end_time = 1391285374
    sites = [1,3,4,5,6,8]
    tmpEvalMan = manualLabelingEvaluation(depID, start_time,
                                          end_time, sites,
                                          validation)
    tmpEvalLik = likelihoodLabelingEvaluation(depID, start_time,
                                              end_time, sites,
                                              validation)
    for i in range(4):
      evalMan[i] += tmpEvalMan[i]
      evalLik[i] += tmpEvalLik[i]

  
  cur = db_con.cursor()
  cur.execute("""INSERT INTO classifier_performance
                 (deploymentID, validation, TP, TN,
                 FP, FN, total_records, classifier_type)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'bandwidth filter')
              """%(depID, validation, evalMan[0], evalMan[1],
                   evalMan[2], evalMan[3], sum(evalMan)))
  cur2 = db_con.cursor()
  cur2.execute("""INSERT INTO classifier_performance2
                  (deploymentID, validation, TP, TN,
                  FP, FN, total_records, classifier_type)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, 'bandwidth filter')
               """%(depID, validation, evalLik[0], evalLik[1],
                    evalLik[2], evalLik[3], sum(evalLik)))

  
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
     This program should evulate all deployment
     and site combinations for bandwidth filter.
     It will do 10 times on different traning
     and validation sets. It will also do it on
     both manual and likelihood labelings.
  """
  
#go through each combination of validation and deployment
  initTime = time.time()
  deploymentIDArray = [57, 60, 61, 62]
  for i in range(10):
    for j in deploymentIDArray:
      evaluation(j, i)

  print time.time() - initTime
  
if __name__ == '__main__':
  main()
