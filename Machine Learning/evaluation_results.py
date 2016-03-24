import MySQLdb
import numpy as np
import time

  
def results(manOrLik):
  deployments = [57, 60, 61, 62]
  methods = ['bandwidth filter', 'estScore Filter', 'NBC',
             'modified BC', 'decisionTree', 'randomForests', 'SVM']
  depDict = {}
  
  db_con = MySQLdb.connect(user="root", db="qraat")
  for i in deployments:
    resultDict = {}
    cur = db_con.cursor()
    cur.execute("""SELECT TP, TN, FP, FN,
                   total_records, classifier_type
                   FROM classifier_performance%s
                   WHERE deploymentID = %s
                """%(manOrLik, i))
    for row in cur.fetchall():
      if row[5] not in resultDict:
        resultDict[row[5]] = [[row[2]/float(row[2] + row[1])],
                              [row[3]/float(row[3] + row[0])],
                              [float(row[2] + row[3]) / row[4]]]
      else:
        resultDict[row[5]][0].append(row[2]/float(row[2] + row[1]))
        resultDict[row[5]][1].append(row[3]/float(row[3] + row[0]))
        resultDict[row[5]][2].append(float(row[2] + row[3]) / row[4])
    depDict[i] = resultDict

  for i in deployments:
    print '\nDeployment %s'%i
    print '%-18s%-9s%-9s%-9s%-9s%-9s%-9s'%('method', 'FP mean', 'FP SD',
                                           'FN mean', 'FN SD', 'ER mean',
                                           'ER SD')
    for j in methods:
      print '%-18s%-9.5f%-9.5f%-9.5f%-9.5f%-9.5f%-9.5f'%(j,
                                                      np.mean(depDict[i][j][0]),
                                                      np.std(depDict[i][j][0]),
                                                      np.mean(depDict[i][j][1]),
                                                      np.std(depDict[i][j][1]),
                                                      np.mean(depDict[i][j][2]),
                                                      np.std(depDict[i][j][2]))
  
  
def main():
  initTime = time.time()
  
  print 'Manual Labeling'
  results('')
  print '\n\nLikelihood Labeling'
  results('2')

  print time.time() - initTime

  
if __name__ == '__main__':
  main()
