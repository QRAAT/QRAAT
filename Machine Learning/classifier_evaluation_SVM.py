import qraatSignal
import MySQLdb
import numpy as np
import time
import math

def rbfKernel(data, x, gamma):
  normSquare = 0
  for i in range(9):
    difference = data[i] - x[i]
    normSquare += difference**2
  return np.exp(-normSquare*gamma)

def SVMPredict(alphaArray, x, y, b, gamma, data):
  f = b
  for i in range(len(alphaArray)):
    f+=alphaArray[i]*y[i]*rbfKernel(data, x[i], gamma)
  if (f > 0):
    return 1
  else:
    return -1

def evaluation(deploymentID, start_time,
               end_time, sites, validation, manOrLik):
  """
     Find the TP, TN, FP, and FN for the deployment and time.
  """
  
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

    y = []
    x = []
    alphaArray = []
    cur.execute("""SELECT isPulse, band3, band10, frequency,
                   ec, tnp, edsp, fdsp, edsnr, fdsnr, alpha
                   FROM est, SVM_alpha%s, est_class%s
                   WHERE est.ID = SVM_alpha%s.estID
                   AND est.ID = est_class%s.estID
                   AND SVM_alpha%s.start_time = %s
                   AND est.deploymentID = %s
                   AND est.siteID = %s
                   AND SVM_alpha%s.validation = %s;
                """%(manOrLik, manOrLik, manOrLik, manOrLik, manOrLik,
                     start_time, deploymentID, i, manOrLik, validation))
    for row in cur.fetchall():
      y.append(row[0])
      x.append(row[1:10])
      alphaArray.append(row[10])

    b = 0
    cur.execute("""SELECT b
                   FROM SVM_b%s
                   WHERE start_time = %s
                   AND deploymentID = %s
                   AND siteID = %s
                   AND validation = %s;
                """%(manOrLik, start_time, deploymentID,
                     i, validation))
    for row in cur.fetchall():
      b = row[0]

    gamma = 0
    cur.execute("""SELECT gamma
                   FROM SVM_gamma%s
                   WHERE start_time = %s
                   AND deploymentID = %s
                   AND siteID = %s
                   AND validation = %s;
                """%(manOrLik, start_time, deploymentID,
                     i, validation))
    for row in cur.fetchall():
      gamma = row[0]
    
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
      estData = row[1:10]
      isPulse = SVMPredict(alphaArray, x, y, b, gamma, estData)

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
  
  evalMan = evaluation(depID, start_time[depID], end_time[depID],
                       sites[depID], validation, '')
  evalLik = evaluation(depID, start_time[depID], end_time[depID],
                       sites[depID], validation, '2')
  
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

  
  cur = db_con.cursor()
  cur.execute("""INSERT INTO classifier_performance
                 (deploymentID, validation, TP, TN,
                 FP, FN, total_records, classifier_type)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'SVM')
              """%(depID, validation, evalMan[0], evalMan[1],
                   evalMan[2], evalMan[3], sum(evalMan)))
  cur2 = db_con.cursor()
  cur2.execute("""INSERT INTO classifier_performance2
                  (deploymentID, validation, TP, TN,
                  FP, FN, total_records, classifier_type)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, 'SVM')
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
  initTime = time.time()
  deploymentIDArray = [57, 60, 61, 62]
  for i in range(10):
    for j in deploymentIDArray:
      insertResults(j, i)

  print time.time() - initTime
  
if __name__ == '__main__':
  main()
