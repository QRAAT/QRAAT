import MySQLdb
import numpy as np
import time
import sys
from sklearn.svm import SVC


def getDataSet(start_time, end_time, deploymentID,
               siteID, validations, manOrLik):
  """
     Query the data set.
  """
  x = []
  y = []
  idArray = []
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  cur = db_con.cursor()
  nonValidations = range(10)
  for i in validations:
    nonValidations.remove(i)
  query = """SELECT band3, band10, frequency,
                 ec, tnp, edsp, fdsp, edsnr, fdsnr,
                 isPulse, ID
                 FROM est INNER JOIN est_class%s
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s
              """%(manOrLik, start_time, end_time, deploymentID,
                   siteID)
  for i in nonValidations:
    query += ' AND setNum != %s'%i

  cur.execute(query+';')
  for row in cur.fetchall():
    idArray.append(row[10])
    x.append(list(row)[0:9])
    if (row[9]==0):
      y.append(-1)
    else:
      y.append(1)
    
  return x,y, idArray


def SVM(deploymentID, site, start_time, end_time,
        validation, manOrLik):
  """This function will be using cross validations to determine the 
     best C and kernel parameters to use in the SVM. The parameters 
     resulting the lowest error rate will be used to train the overall
     dataset.
     If corss validation takes too long, use hide out method instead.
  """

  numberOfSamplePoints = 1000

  bestC = 0
  bestGamma = 0
  bestErrorRate = 1
  CArray = [2**i for i in range(-5,16,3)]
  gammaArray = [2**i for i in range(-15,4,3)]
  
  #Grid seach for each combination of possibly C and gamma
  for i in CArray:
    for j in gammaArray:

      ## do held-out of 20% instead
      training = range(10)
      training.pop(validation)
      validations = []
      for k in range(2):
        np.random.seed()
        randIdx = np.random.randint(len(training))
        validations.append(training[randIdx])
        training.pop(randIdx)
      
      trainingX, trainingY, idArray = getDataSet(start_time, end_time, deploymentID,
                                                 site, training, manOrLik)
      validationX, validationY, idArray = getDataSet(start_time, end_time, deploymentID,
                                                     site, validations, manOrLik)
      #bootstrap the data if its too big
      if (len(trainingX) > numberOfSamplePoints):
        np.random.seed()
        tmpX = []
        tmpY = []
        for l in range(numberOfSamplePoints):
          randIdx = np.random.randint(len(trainingX))
          tmpX.append(trainingX[randIdx])
          tmpY.append(trainingY[randIdx])
        trainingX = tmpX
        trainingY = tmpY
      trainingX = np.array(trainingX)
      trainingY = np.array(trainingY)
      trainingYSet = set(trainingY)
      
      #only train data with SVM if it has 2 classes
      if (len(trainingYSet) == 2):
        clf = SVC()
        clf.fit(trainingX, trainingY) 
        SVC(C=i, cache_size=2000, class_weight=None, coef0=0.0,
            decision_function_shape=None, degree=3, gamma=j, kernel='rbf',
            max_iter=-1, probability=False, random_state=None, shrinking=True,
            tol=0.001, verbose=False)
            
        #calculate error with the trained model
        error = 0
        for l in range(len(validationY)):
          isPulse = clf.predict([validationX[l]])
          if (isPulse != validationY[l]):
            error += 1
      else:
        predictClass = trainingY[0]
        error = 0
        for l in range(len(validationY)):
          if (predictClass != validationY[l]):
            error += 1

      #keep the pair with the lowest error rate
      currentErrorRate = float(error)/len(validationY)
      if (currentErrorRate < bestErrorRate):
        bestErrorRate = currentErrorRate
        bestC = i
        bestGamma = j

  print deploymentID, site, bestC, bestGamma, bestErrorRate
        
  #insert best gamma into database
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  cur = db_con.cursor()
  cur.execute("""INSERT INTO SVM_gamma%s
                 (deploymentID, siteID,
                 start_time, validation, gamma)
                 VALUES (%s, %s, %s, %s, %s);
              """%(manOrLik, deploymentID, site, start_time,
                   validation, bestGamma))
    
  #calculate alphaArray and b for the best c and gamma settings
  training = range(10)
  training.pop(validation)
  trainingX, trainingY, idArray = getDataSet(start_time, end_time, deploymentID,
                                             site, training, manOrLik)
  if (len(trainingX) > numberOfSamplePoints):
    np.random.seed()
    tmpX = []
    tmpY = []
    tmpID = []
    for l in range(numberOfSamplePoints):
      randIdx = np.random.randint(len(trainingX))
      tmpX.append(trainingX[randIdx])
      tmpY.append(trainingY[randIdx])
      tmpID.append(idArray[randIdx])
    trainingX = tmpX
    trainingY = tmpY
    idArray = tmpID
  trainingX = np.array(trainingX)
  trainingY = np.array(trainingY)
  trainingYSet = set(trainingY)
  alphaArray = {}
  b = 0
  if (len(trainingYSet) == 2):
    clf = SVC()
    clf.fit(trainingX, trainingY) 
    SVC(C=i, cache_size=2000, class_weight=None, coef0=0.0,
        decision_function_shape=None, degree=3, gamma=j, kernel='rbf',
        max_iter=-1, probability=False, random_state=None, shrinking=True,
        tol=0.001, verbose=False)
    for i in range(len(clf.support_)):
      alphaArray[idArray[clf.support_[i]]] = clf.dual_coef_[0][i]
    b = clf.intercept_[0]
  elif len(trainingYSet) == 1:
    b = trainingY[0]

  #insert alphaArray and b into database
  cur = db_con.cursor()
  cur.execute("""INSERT INTO SVM_b%s
                 (deploymentID, siteID,
                 start_time, validation, b)
                 VALUES (%s, %s, %s, %s, %s);
              """%(manOrLik, deploymentID, site, start_time,
                   validation, b))
  for i in alphaArray:
    cur = db_con.cursor()
    cur.execute("""INSERT INTO SVM_alpha%s
                   (deploymentID, siteID, start_time,
                   validation, estID, alpha)
                   VALUES (%s, %s, %s, %s, %s, %s);
                """%(manOrLik, deploymentID, site, start_time,
                     validation, i, alphaArray[i]))
    

def main():
  """
     This program will train SVM. It will use grid search to find the 
     best parameters for SVM using 1000 bootstrip points and a 20% held-out
     to calculate the error. With the best pair of parameters, it will then 
     train the svm using 1000 bootstriped points from the entire set. It will
     then store all the trained values into the database.
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
  
  #Loop through each combination of validation, deployment, and sites.
  for i in range(10):
    for j in deploymentIDArray:
      for k in sites[j]:
        SVM(j, k, start_time[j], end_time[j],
            i, '')
        SVM(j, k, start_time[j], end_time[j],
            i, '2')

      if ((j == 61)|(j == 62)):
        for k in [1,3,4,5,6,8]:
          SVM(j, k, 1391276584, 1391285374, i, '')
          SVM(j, k, 1391276584, 1391285374, i, '2')
          
      print "deployment %s, validation %s done"%(j, i)
      print time.time() - initTime
      
  print time.time() - initTime


if __name__ == '__main__':
  main()
