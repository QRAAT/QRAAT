import MySQLdb
import numpy as np
import time
from scipy.stats import norm

def probabilityOfDiscreteData(deploymentID, siteID, start_time, end_time,
                              validation, manOrLik):
  """
     This program will query the data from band3, band10, and frequency.
     It then calculate the probability of each unique values and normalize
     the probabilities. It then store the results in probability_of_discrete_data
     table.
  """
  
  band3 = {}
  band10 = {}
  frequency = {}
  
  #query the count of each unique values
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  cur = db_con.cursor()
  cur.execute("""SELECT distinct band3, count(band3) AS countOf
                 FROM est INNER JOIN est_class%s
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND isPulse = 1
                 AND setNum != %s
                 GROUP BY band3;
              """%(manOrLik, start_time, end_time,
                   deploymentID, siteID, validation))
  for row in cur.fetchall():
    band3[row[0]] = row[1]
    
  cur.execute("""SELECT distinct band10, count(band10) AS countOf
                 FROM est INNER JOIN est_class%s
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND isPulse = 1
                 AND setNum != %s
                 GROUP BY band10;
              """%(manOrLik, start_time, end_time,
                   deploymentID, siteID, validation))
  for row in cur.fetchall():
    band10[row[0]] = row[1]

  cur.execute("""SELECT distinct frequency, count(frequency) AS countOf
                 FROM est INNER JOIN est_class%s
                 ON ID = estID
                 WHERE timestamp > %s
                 AND timestamp < %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND isPulse = 1
                 AND setNum != %s
                 GROUP BY frequency;
              """%(manOrLik, start_time, end_time,
                   deploymentID, siteID, validation))
  for row in cur.fetchall():
    frequency[row[0]] = row[1]

  #query the mean and variance for normalize the probabilities.
  cur.execute("""SELECT band3_mean, band3_var, band10_mean, band10_var,
                 frequency_mean, frequency_var
                 FROM est_mean_and_var%s
                 WHERE start_time = %s
                 AND validation = %s
                 AND deploymentID = %s
                 AND siteID = %s
                 AND isPulse = 1;
              """%(manOrLik, start_time, validation,
                   deploymentID, siteID))
  for row in cur.fetchall():
    band3Dist = norm(loc = row[0], scale = np.sqrt(row[1]))
    band10Dist = norm(loc = row[2], scale = np.sqrt(row[3]))
    frequencyDist = norm(loc = row[4], scale = np.sqrt(row[5]))
  
  #calculate the normalization scales
  band3Scale = band3Dist.cdf(max(band3)) - band3Dist.cdf(min(band3))
  band10Scale = band10Dist.cdf(max(band10)) - band10Dist.cdf(min(band10))
  frequencyScale = frequencyDist.cdf(max(frequency)) - frequencyDist.cdf(min(frequency))
  totalRecords = sum(band3.values())

  #store the unique values with normalizated probabilities into the database.
  for i in band3:
    cur2 = db_con.cursor()
    cur2.execute("""INSERT INTO probability_of_discrete_data%s
                    (deploymentID, siteID, start_time, validation,
                    data_type, data_value, probability)
                    VALUES (%s, %s, %s, %s, 'band3', %s, %s)
                 """%(manOrLik, deploymentID, siteID, start_time,
                      validation, i, band3Scale*band3[i]/totalRecords))
  for i in band10:
    cur2 = db_con.cursor()
    cur2.execute("""INSERT INTO probability_of_discrete_data%s
                    (deploymentID, siteID, start_time, validation,
                    data_type, data_value, probability)
                    VALUES (%s, %s, %s, %s, 'band10', %s, %s)
                 """%(manOrLik, deploymentID, siteID, start_time,
                      validation, i, band10Scale*band10[i]/totalRecords))
  for i in frequency:
    cur2 = db_con.cursor()
    cur2.execute("""INSERT INTO probability_of_discrete_data%s
                    (deploymentID, siteID, start_time, validation,
                    data_type, data_value, probability)
                    VALUES (%s, %s, %s, %s, 'frequency', %s, %s)
                 """%(manOrLik, deploymentID, siteID, start_time,
                      validation, i, frequencyScale*frequency[i]/totalRecords))
    
def meanAndVar(deploymentID, sites, start_time, end_time,
               validation, manOrLik):
  db_con = MySQLdb.connect(user = "root", db = "qraat")
  
  #loop through each site
  for i in sites:
    totalRecords = 0
    goodRecords = 0
    badRecords = 0
    goodTrainingSet = {'band3':[], 'band10':[],
                       'frequency':[], 'ec':[], 'tnp':[],
                       'edsp':[], 'fdsp':[],
                       'edsnr':[], 'fdsnr':[]}
    badTrainingSet = {'band3':[], 'band10':[],
                      'frequency':[], 'ec':[], 'tnp':[],
                      'edsp':[], 'fdsp':[],
                      'edsnr':[], 'fdsnr':[]}
    
    #query data
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
                """%(manOrLik, start_time, end_time,
                     deploymentID, i, validation))
    
    for row in cur.fetchall():
      totalRecords += 1
      if (row[9] == 1):
        goodRecords += 1
        goodTrainingSet['band3'].append(row[0])
        goodTrainingSet['band10'].append(row[1])
        goodTrainingSet['frequency'].append(row[2])
        goodTrainingSet['ec'].append(row[3])
        goodTrainingSet['tnp'].append(row[4])
        goodTrainingSet['edsp'].append(row[5])
        goodTrainingSet['fdsp'].append(row[6])
        goodTrainingSet['edsnr'].append(row[7])
        goodTrainingSet['fdsnr'].append(row[8])
      else:
        badRecords += 1
        badTrainingSet['band3'].append(row[0])
        badTrainingSet['band10'].append(row[1])
        badTrainingSet['frequency'].append(row[2])
        badTrainingSet['ec'].append(row[3])
        badTrainingSet['tnp'].append(row[4])
        badTrainingSet['edsp'].append(row[5])
        badTrainingSet['fdsp'].append(row[6])
        badTrainingSet['edsnr'].append(row[7])
        badTrainingSet['fdsnr'].append(row[8])

    #store the mean and the variance for each variable.
    if (goodRecords != 0):
      cur2 = db_con.cursor()
      cur2.execute("""INSERT INTO est_mean_and_var%s
                      (deploymentID, siteID, start_time, validation,
                      probability, band3_mean, band3_var, band10_mean,
                      band10_var, frequency_mean, frequency_var,
                      ec_mean, ec_var, tnp_mean, tnp_var,
                      edsp_mean, edsp_var, fdsp_mean, fdsp_var,
                      edsnr_mean, edsnr_var, fdsnr_mean, fdsnr_var, isPulse)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                   """%(manOrLik, deploymentID, i, start_time, validation,
                        float(goodRecords)/totalRecords, 
                        np.mean(goodTrainingSet['band3']),
                        np.var(goodTrainingSet['band3']),
                        np.mean(goodTrainingSet['band10']),
                        np.var(goodTrainingSet['band10']),
                        np.mean(goodTrainingSet['frequency']),
                        np.var(goodTrainingSet['frequency']),
                        np.mean(goodTrainingSet['ec']),
                        np.var(goodTrainingSet['ec']),
                        np.mean(goodTrainingSet['tnp']),
                        np.var(goodTrainingSet['tnp']),
                        np.mean(goodTrainingSet['edsp']),
                        np.var(goodTrainingSet['edsp']),
                        np.mean(goodTrainingSet['fdsp']),
                        np.var(goodTrainingSet['fdsp']),
                        np.mean(goodTrainingSet['edsnr']),
                        np.var(goodTrainingSet['edsnr']),
                        np.mean(goodTrainingSet['fdsnr']),
                        np.var(goodTrainingSet['fdsnr'])))
    else:
      cur2 = db_con.cursor()
      cur2.execute("""INSERT INTO est_mean_and_var%s
                      (deploymentID, siteID, start_time, validation,
                      probability, band3_mean, band3_var, band10_mean,
                      band10_var, frequency_mean, frequency_var,
                      ec_mean, ec_var, tnp_mean, tnp_var,
                      edsp_mean, edsp_var, fdsp_mean, fdsp_var,
                      edsnr_mean, edsnr_var, fdsnr_mean, fdsnr_var, isPulse)
                      VALUES (%s, %s, %s, %s, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
                   """%(manOrLik, deploymentID, i, start_time, validation))
      
    if (badRecords != 0):
      cur3 = db_con.cursor()
      cur3.execute("""INSERT INTO est_mean_and_var%s
                      (deploymentID, siteID, start_time, validation,
                      probability, band3_mean, band3_var, band10_mean,
                      band10_var, frequency_mean, frequency_var,
                      ec_mean, ec_var, tnp_mean, tnp_var,
                      edsp_mean, edsp_var, fdsp_mean, fdsp_var,
                      edsnr_mean, edsnr_var, fdsnr_mean, fdsnr_var, isPulse)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                   """%(manOrLik, deploymentID, i, start_time, validation,
                        float(badRecords)/totalRecords,
                        np.mean(badTrainingSet['band3']),
                        np.var(badTrainingSet['band3']),
                        np.mean(badTrainingSet['band10']),
                        np.var(badTrainingSet['band10']),
                        np.mean(badTrainingSet['frequency']),
                        np.var(badTrainingSet['frequency']),
                        np.mean(badTrainingSet['ec']),
                        np.var(badTrainingSet['ec']),
                        np.mean(badTrainingSet['tnp']),
                        np.var(badTrainingSet['tnp']),
                        np.mean(badTrainingSet['edsp']),
                        np.var(badTrainingSet['edsp']),
                        np.mean(badTrainingSet['fdsp']),
                        np.var(badTrainingSet['fdsp']),
                        np.mean(badTrainingSet['edsnr']),
                        np.var(badTrainingSet['edsnr']),
                        np.mean(badTrainingSet['fdsnr']),
                        np.var(badTrainingSet['fdsnr'])))
    else:
      cur2 = db_con.cursor()
      cur2.execute("""INSERT INTO est_mean_and_var%s
                      (deploymentID, siteID, start_time, validation,
                      probability, band3_mean, band3_var, band10_mean,
                      band10_var, frequency_mean, frequency_var,
                      ec_mean, ec_var, tnp_mean, tnp_var,
                      edsp_mean, edsp_var, fdsp_mean, fdsp_var,
                      edsnr_mean, edsnr_var, fdsnr_mean, fdsnr_var, isPulse)
                      VALUES (%s, %s, %s, %s, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                   """%(manOrLik, deploymentID, i, start_time, validation))
                       
  #calculate the normalized mixed distribution.
  for i in sites:
    probabilityOfDiscreteData(deploymentID, i, start_time, end_time,
                              validation, manOrLik)

def main():
  """
     This program will calculate the mean and the variance for pulse and
     noise for each of the combination of deployment, site, variable, and labeling.
     It will also calculate the normalized mixed probability for band3, band10, and
     frequency.
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
  
  #loop through each combinatoin of site and deployment.
  for i in range(10):
    for j in deploymentIDArray:
      meanAndVar(j, sites[j], start_time[j], end_time[j],
                 i, '')
      meanAndVar(j, sites[j], start_time[j], end_time[j],
                 i, '2')
      if ((j == 61)|(j == 62)):
        meanAndVar(j, [1,3,4,5,6,8], 1391276584, 1391285374,
                   i, '')
        meanAndVar(j, [1,3,4,5,6,8], 1391276584, 1391285374,
                   i, '2')
      print "deployment %s, validation %s done"%(j, i)
      

  print time.time() - initTime
  
  
  
  print 'done'
if __name__ == '__main__':
  main()
