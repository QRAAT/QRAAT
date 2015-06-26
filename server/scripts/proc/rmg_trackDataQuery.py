#!/usr/bin/env python2
# rmg_trackDataQuery.py
#
# Written by Gene Der Su for QRAAT project in summer 2015
#
# This script querys the movebank_export table as inputs.
# It then queries the track data for each animal from the last upload time
# to the current time and returns current time, deployment ID, studuy ID,
# format ID, and file name for the movebankUpload.py to use.


import MySQLdb
import csv
import time
from time import strftime
import sys
import os
import qraat
import qraat.srv

def main():
    ## Setup MySQL connector for later use
#    db = MySQLdb.connect(
##                     host="localhost", # your host, usually localhost
##                     user="writer", # your username
##                     passwd="KJsBA!Zl", # your password
#                     host="127.0.0.1", # your host, usually localhost
#                     port=13306,
#                     user="gene", # your username
#                     passwd="YVsNsE6B", # your password
#                     db="qraat") # name of the data base
    db=qraat.srv.util.get_db('web_reader')

    ## Query on the information for export
    cur = db.cursor()
    currentTime=time.time()
    query=("SELECT * FROM movebank_export WHERE enable=1 AND "
           "time_last_export+export_interval<=%s")%(currentTime)
    cur.execute(query)

    ## Initialize arrays
    deploymentIDArray=[]
    studyIDArray=[]
    formatIDArray=[]
    fileNameArray=[]

    ## Loop through the movebank_export rows
    for exportRow in cur.fetchall() :
        deploymentIDArray.append(int(exportRow[1]))
        studyIDArray.append(int(exportRow[4]))
        formatIDArray.append(int(exportRow[5]))
        
        ## Execute the query
        cur2 = db.cursor()
        cur2.execute ("""
           SELECT target.name, deployment.targetID, 
           track_pos.timestamp, position.latitude,
           position.longitude, position.likelihood, position.activity
           FROM target INNER JOIN deployment ON target.ID=deployment.targetID
           INNER JOIN track_pos ON deployment.ID=track_pos.deploymentID
           INNER JOIN position ON position.ID=track_pos.positionID
           WHERE track_pos.deploymentID=%s AND track_pos.timestamp>=%s
           AND track_pos.timestamp<=%s
        """, (exportRow[1], exportRow[2], currentTime))

        ## Creating the csv file and writing the content
        fileName = '/tmp/Deployment%s_%s-%s.csv' %(exportRow[1],exportRow[2], currentTime)
        fileNameArray.append(fileName)
        
        with open(fileName, 'wb') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',',
                            quotechar=';', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(['name', 'targetID', 'timestamp', 'latitude', 'longitude', 'likelihood', 'activity'])
            for dataRow in cur2.fetchall() :
                t=time.gmtime(float(dataRow[2]))
                timeString="%s-%s-%s %s:%s:%s"%(strftime("%Y", t),strftime("%m", t),strftime("%d", t),strftime("%H", t),strftime("%M", t),strftime("%S", t))
                spamwriter.writerow([dataRow[0], dataRow[1], timeString, dataRow[3], dataRow[4], dataRow[5], dataRow[6]])

    print "Data pulling is done."
    print ""
    
    return currentTime, deploymentIDArray, studyIDArray, formatIDArray, fileNameArray

if __name__=='__main__':
##    sys.exit(main(sys.argv[1]))
    sys.exit(main())


