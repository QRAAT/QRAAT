import MySQLdb
import numpy as np

def setNumLikelihood(deploymentID, start_time, end_time, site):
  """
     Set the validation number to each of the est in likelihood labeling.
  """

  #Create a counter array to keep track how much observations each block needs
  db_con = MySQLdb.connect(user="root", db="qraat")
  cur = db_con.cursor()
  cur.execute("""SELECT COUNT(*) FROM est
                 INNER JOIN est_class2
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s;
              """%(start_time, end_time, deploymentID, site))
  total = cur.fetchall()[0][0]
  counter = [total/10]*10
  for i in range(total%10):
    counter[i] += 1

  #Randomly assign validations to each est and insert it to the labeling
  cur2 = db_con.cursor()
  cur2.execute("""SELECT estID FROM est
                  INNER JOIN est_class2
                  ON ID = estID
                  WHERE timestamp > %s
                  AND timestamp < %s
                  AND deploymentID = %s
                  AND siteID = %s;
              """%(start_time, end_time, deploymentID, site))
  for row in cur2.fetchall():
    np.random.seed()
    setNumber = np.random.randint(10)
    if (counter[setNumber] > 0):
      counter[setNumber] -= 1
    else:
      setNumber += 1
      while (counter[setNumber%10] == 0):
        setNumber += 1
      setNumber = setNumber%10
      counter[setNumber] -= 1
    
    cur3 = db_con.cursor()
    cur3.execute("""UPDATE est_class2
                    SET setNum = %s
                    WHERE estID = %s;
                 """%(setNumber, row[0]))

def setNumManual(deploymentID, start_time, end_time, site):
  """
     Set the validation number to each of the est in  manual labeling.
  """
    
  #Create a counter array to keep track how much observations each block needs
  db_con = MySQLdb.connect(user="root", db="qraat")
  cur = db_con.cursor()
  cur.execute("""SELECT COUNT(*) FROM est
                 INNER JOIN est_class
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s;
              """%(start_time, end_time, deploymentID, site))
  total = cur.fetchall()[0][0]
  counter = [total/10]*10
  for i in range(total%10):
    counter[i] += 1

  #Randomly assigned validations to each est and insert it to the labeling
  cur2 = db_con.cursor()
  cur2.execute("""SELECT estID FROM est
                  INNER JOIN est_class
                  ON ID = estID
                  WHERE timestamp > %s
                  AND timestamp < %s
                  AND deploymentID = %s
                  AND siteID = %s;
              """%(start_time, end_time, deploymentID, site))
  for row in cur2.fetchall():
    np.random.seed()
    setNumber = np.random.randint(10)
    if (counter[setNumber] > 0):
      counter[setNumber] -= 1
    else:
      setNumber += 1
      while (counter[setNumber%10] == 0):
        setNumber += 1
      setNumber = setNumber%10
      counter[setNumber] -= 1
    
    cur3 = db_con.cursor()
    cur3.execute("""UPDATE est_class
                    SET setNum = %s
                    WHERE estID = %s;
                 """%(setNumber, row[0]))

def main():
  """
     This program will set the validation number to each est.
     The number of the est's in each validation set is set to
     be nearly equally sized blocks by keeping track of how
     many est's can still be in a single validation. The data
     is stored in est_class table.
  """
  
  deploymentID = [57, 60, 61, 62]
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
  
  #Loop through each combination of deployment and site
  for i in deploymentID:
    for j in sites[i]:
      setNumManual(i, start_time[i], end_time[i], j)
      setNumLikelihood(i, start_time[i], end_time[i], j)
      print "deployment: %s, site: %s is done"%(i,j)
    
    #additional trackings for deployment 61 and 62
    if ((i == 61)|(i == 62)):
      for j in [1,3,4,5,6,8]:
        setNumManual(i, 1391276584, 1391285374, j)
        setNumLikelihood(i, 1391276584, 1391285374, j)
  
  print 'done'

if __name__ == '__main__':
  main()
