#!/usr/bin/env python2
# rmg_movebankExport.py
#
# Written by Gene Der Su for QRAAT project in summer 2015
#
# This script uses the data that are pulled from query script
# to upload them onto Movebank

import pycurl
import rmg_trackDataQuery
import MySQLdb
import os
import qraat
import qraat.srv

## Getting the all inputs from the script.
[currentTime, deploymentIDArray, studyIDArray, formatIDArray, fileNameArray]= rmg_trackDataQuery.main()

## Setup MySQL connector for later use
#db = MySQLdb.connect(
##                        host="localhost", # your host, usually localhost
##                        user="writer", # your username
##                        passwd="KJsBA!Zl", # your password
#                        host="127.0.0.1", # your host, usually localhost
#                        port=13306,
#                        user="gene", # your username
#                        passwd="YVsNsE6B", # your password
#                        db="qraat") # name of the data base
db=qraat.srv.util.get_db('web_writer')

## Loop through the file names and upload each of them onto Movebank
for idx, val in enumerate(fileNameArray):
    currentCurl = pycurl.Curl()
    values = [
         ("input-format", str(formatIDArray[idx])),
         ("study", str(studyIDArray[idx])),
         ("file-bytes", (pycurl.FORM_FILE, val))
    ]
    currentCurl.setopt(pycurl.URL, 'https://www.movebank.org/movebank/service/import')
    currentCurl.setopt(pycurl.USERPWD, "gdsu:1234Abc!")
    currentCurl.setopt(pycurl.HTTPPOST, values)
    currentCurl.perform()
    currentCurl.close()
    print "Deployment %s export complete."%(deploymentIDArray[idx])

    ## Remove the data file
    os.remove(val) #comment out this line if you wish to keep all the files in the same directory!!!

    ## Update the time_last_export in the movebank_export table
    cur = db.cursor()
    cur.execute ("""
           UPDATE movebank_export
           SET time_last_export=%s
           WHERE deploymentID=%s
    """, (currentTime, deploymentIDArray[idx]))

## Print something so the user know the procedure is done.
print ""
print "All export complete."
