import MySQLdb
import numpy as np
import time
import random


def bestSplit(trainingSet, dataTypeIndex):
  """Given a set of data and data type. It calculates
     the best value for split and the entropy. The branch
     if splited by <= of the value. If the total number of
     records > 100, check only 100 values equally distrubted
     between max and min, else check all values.
  """
  bestEntropy = 1
  bestValue = -1
  
  #Checking all possible values.
  if (len(trainingSet) <= 100):
    for i in range(len(trainingSet)):
      leftPulse = 0
      rightPulse = 0
      leftCount = 0
      rightCount = 0
      currentEntropy = 0
      leftPulseProportion = 0
      rightPulseProportion = 0
      for j in range(len(trainingSet)):
        if (trainingSet[j][dataTypeIndex] <= trainingSet[i][dataTypeIndex]):
          leftCount += 1
          if (trainingSet[j][9] == 1):
            leftPulse += 1
        else:
          rightCount += 1
          if (trainingSet[j][9] == 1):
            rightPulse += 1
            
      if (leftCount != 0):
        leftPulseProportion = float(leftPulse)/leftCount
      if (rightCount != 0):
        rightPulseProportion = float(rightPulse)/rightCount
        
      if ((leftPulseProportion != 0)&
          (leftPulseProportion != 1)):
        currentEntropy += float(leftCount)/len(trainingSet)*\
                          (-leftPulseProportion*np.log(leftPulseProportion) \
                          -(1 - leftPulseProportion)*np.log(1-leftPulseProportion))
      if ((rightPulseProportion != 0)&
          (rightPulseProportion != 1)):
        currentEntropy += float(rightCount)/len(trainingSet)*\
                          (-rightPulseProportion*np.log(rightPulseProportion) \
                          -(1 - rightPulseProportion)*np.log(1-rightPulseProportion))
        
      if (currentEntropy < bestEntropy):
        bestEntropy = currentEntropy
        bestValue = trainingSet[i][dataTypeIndex]
        
  else:
    minValue = 10**10
    maxValue = -1
    for i in range(len(trainingSet)):
      if (trainingSet[i][dataTypeIndex] < minValue):
        minValue = trainingSet[i][dataTypeIndex]
      if (trainingSet[i][dataTypeIndex] > maxValue):
        maxValue = trainingSet[i][dataTypeIndex]

    #Check only 100 intervals between min and max
    valueInterval = (maxValue - minValue)/100.0
    for i in range(100):
      leftPulse = 0
      rightPulse = 0
      leftCount = 0
      rightCount = 0
      currentEntropy = 0
      leftPulseProportion = 0
      rightPulseProportion = 0
      for j in range(len(trainingSet)):
        if (trainingSet[j][dataTypeIndex] <= minValue + i*valueInterval):
          leftCount += 1
          if (trainingSet[j][9] == 1):
            leftPulse += 1
        else:
          rightCount += 1
          if (trainingSet[j][9] == 1):
            rightPulse += 1
            
      if (leftCount != 0):
        leftPulseProportion = float(leftPulse)/leftCount
      if (rightCount != 0):
        rightPulseProportion = float(rightPulse)/rightCount
        
      if ((leftPulseProportion != 0)&
          (leftPulseProportion != 1)):
        currentEntropy += float(leftCount)/len(trainingSet)*\
                          (-leftPulseProportion*np.log(leftPulseProportion) \
                          -(1 - leftPulseProportion)*np.log(1-leftPulseProportion))
      if ((rightPulseProportion != 0)&
          (rightPulseProportion != 1)):
        currentEntropy += float(rightCount)/len(trainingSet)*\
                          (-rightPulseProportion*np.log(rightPulseProportion) \
                          -(1 - rightPulseProportion)*np.log(1-rightPulseProportion))        

      if (currentEntropy < bestEntropy):
        bestEntropy = currentEntropy
        bestValue = minValue + i*valueInterval
        
  return bestEntropy, bestValue
  

def decisionTree(deploymentID, site, start_time, end_time,
                 validation, manOrLik, trainingSet, branchID,
                 treeNum):
  
  """Given a set of data, It calculates the entropy at each
     possible splits. Keep the data type and value for the
     best split. Determine if it needs to continue on each
     of left and right branches. Terminates if the region
     gets less than 1 records, or all records has the same class.
  """
  minRecords = 1
  dataTypes = ['band3', 'band10', 'frequency',
               'ec', 'tnp', 'edsp', 'fdsp',
               'edsnr', 'fdsnr']
  bestEntropy = 1
  bestValue = -1
  bestDataTypeIndex = -1
  
  #Sample 3 random variables to check for best split
  for i in random.sample(range(len(dataTypes)),3):
    currentEntropy, currentValue = bestSplit(trainingSet, i)
    if (currentEntropy < bestEntropy):
      bestEntropy = currentEntropy
      bestValue = currentValue
      bestDataTypeIndex = i

  #Create a branch for this split
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  cur = db_con.cursor()
  cur.execute("""INSERT INTO random_forests%s
                 (deploymentID, siteID, start_time, validation,
                 tree_number, branchID, data_type, data_value)
                 VALUES (%s, %s, %s, %s, %s, '%s', %s, %s);
              """%(manOrLik, deploymentID, site, start_time,
                   validation, treeNum, branchID,
                   bestDataTypeIndex, bestValue))


  #Split data into left and right while keep track if
  #each left and rigth child meet the termination condition.
  leftTrainingSet =[]
  rightTrainingSet = []
  leftPulseCount = 0
  rightPulseCount = 0
  leftFeatures = []
  rightFeatures = []
  leftSameFeatures = 1
  rightSameFeatures = 1
  for i in range(len(trainingSet)):
    if (trainingSet[i][bestDataTypeIndex] <= bestValue):
      leftTrainingSet.append(trainingSet[i])
      if (trainingSet[i][9] == 1):
        leftPulseCount += 1
      if (leftFeatures != []):
        if (leftFeatures[0:9] == trainingSet[i][0:9]):
          leftSameFeatures += 1
      else:
        leftFeatures = trainingSet[i]
    else:
      rightTrainingSet.append(trainingSet[i])
      if (trainingSet[i][9] == 1):
        rightPulseCount += 1
      if (rightFeatures != []):
        if (rightFeatures[0:9] == trainingSet[i][0:9]):
          rightSameFeatures += 1
      else:
        rightFeatures = trainingSet[i]

  #If the termination condition is met, create a leaf node.
  if ((len(leftTrainingSet) <= minRecords)|
      (len(leftTrainingSet) == leftPulseCount)|
      (leftPulseCount == 0)|
      (len(leftTrainingSet) == leftSameFeatures)):
    cur.execute("""INSERT INTO random_forests%s
                   (deploymentID, siteID, start_time, validation,
                   tree_number, branchID, data_type, data_value)
                   VALUES (%s, %s, %s, %s, %s, '%s', 9, %s);
                """%(manOrLik, deploymentID, site, start_time,
                     validation, treeNum, branchID + '1',
                     int(leftPulseCount>(len(leftTrainingSet)-leftPulseCount))))
  else:
    decisionTree(deploymentID, site, start_time, end_time,
                 validation, manOrLik, leftTrainingSet,
                 branchID + '1', treeNum)

  if ((len(rightTrainingSet) <= minRecords)|
      (len(rightTrainingSet) == rightPulseCount)|
      (rightPulseCount == 0)|
      (len(rightTrainingSet) == rightSameFeatures)):
    cur.execute("""INSERT INTO random_forests%s
                   (deploymentID, siteID, start_time, validation,
                   tree_number, branchID, data_type, data_value)
                   VALUES (%s, %s, %s, %s, %s, '%s', 9, %s);
                """%(manOrLik, deploymentID, site, start_time,
                     validation, treeNum, branchID + '0',
                     int(rightPulseCount>(len(rightTrainingSet)-rightPulseCount))))
  else:
    decisionTree(deploymentID, site, start_time, end_time,
                 validation, manOrLik, rightTrainingSet,
                 branchID + '0', treeNum)

  
 
def getTrainingSet(start_time, end_time, deploymentID,
                   siteID, validation, manOrLik):
  """
     Query training set to build the decision tree.
  """
  trainingSet = []
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  cur = db_con.cursor()
  cur.execute("""SELECT band3, band10, frequency,
                 ec, tnp, edsp, fdsp, edsnr, fdsnr,
                 isPulse
                 FROM est INNER JOIN est_class%s
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND setNum != %s;
              """%(manOrLik, start_time, end_time, deploymentID,
                   siteID, validation))
  for row in cur.fetchall():
    trainingSet.append(list(row))
  return trainingSet


def randomForests(deploymentID, site, start_time, end_time,
                  validation, manOrLik):
  """
     Create 9 trees with boostriped data.
  """
  numberOfTree = 9
  trainingSet = getTrainingSet(start_time, end_time, deploymentID,
                               site, validation, manOrLik)
  for i in range(numberOfTree):
    np.random.seed()
    tmpTrainingSet = []
    for j in range(len(trainingSet)):
      tmpTrainingSet.append(trainingSet[np.random.randint(len(trainingSet))])
    decisionTree(deploymentID, site, start_time, end_time,
                 validation, manOrLik, tmpTrainingSet, '', i)
  

def main():
  """
     This program will train 9 bagged decision trees for each combination 
     of deployment, site, and validations. It will store each of the 9 trees
     into the database.
  """
  initTime = time.time()
  
  deploymentIDArray = [57, 60, 61, 62]
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
  
  #Loop through each validation, deployment, and site
  for i in range(10):
    for j in deploymentIDArray:
      for k in sites[j]:
        randomForests(j, k, start_time[j], end_time[j],
                     i, '')
        randomForests(j, k, start_time[j], end_time[j],
                     i, '2')

      if ((j == 61)|(j == 62)):
        for k in [1,3,4,5,6,8]:
          randomForests(j, k, 1391276584, 1391285374,
                       i, '')
          randomForests(j, k, 1391276584, 1391285374,
                       i, '2')
      print "deployment %s, validation %s done"%(j, i)
      print time.time() - initTime
      
  print time.time() - initTime


if __name__ == '__main__':
  main()
