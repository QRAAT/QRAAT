import MySQLdb
import numpy as np
import matplotlib.pyplot as plt
import time
 

def positionPlot(deploymentID, normalize, likelihood):
  count = 0
  db_con = MySQLdb.connect(user="root", db="qraat")
  cur = db_con.cursor()
  cur.execute("""
                 SELECT count(*)
                 FROM position_non_normalized
                 WHERE deploymentID = %s
                 AND isNormalized = %s
                 AND likelihood > %s;
              """%(deploymentID, normalize, likelihood))
  for row in cur.fetchall():
    count = row[0]

  return count


def main():
  start_time = {142:1461884300,
                116:1435782759}
  end_time = {142:1461886955,
              116:1436713781}
  sites = {142:[2,11,12,13],
           116:[2,11,12,13]}

  likelihood = {142:{0:[10.0/100*i for i in xrange(100)],
                     1:[0.034200200/100*i for i in xrange(100)]},
                116:{0:[10.0/100*i for i in xrange(100)],
                     1:[0.035361030/100*i for i in xrange(100)]}}
  
  for i in [142, 116]:
    for j in [0, 1]:
      countArray = []
      for k in likelihood[i][j]:
        countArray.append(positionPlot(i, j, k))
      plt.plot(likelihood[i][j], countArray)
      plt.xlabel('Likelihood Threshold')
      plt.ylabel('Number of Positions')
      if j == 0:
        plt.title('Likelihood Threshold vs Number of Position: deployment %s, non-normalized'%i)
      else:
        plt.title('Likelihood Threshold vs Number of Position: deployment %s, normalized'%i)
      plt.show()
  
  
if __name__ == '__main__':
  main()
