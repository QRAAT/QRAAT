**General Process for the Analysis:**

1. Calculate bearing likelihood using *bearingCalculation.py*
2. Add *position_non_normalized* table to the database.
3. Calclate the positions using *positionCalculation.py*
4. Use *numberOfPositionVsThreshold.py* to figure out which likelihood threshod used to plot positions.
5. Plot *positions using positionPlots.py*


**Scripts:**

- *bearingCalculation.py* - Calculate bearing used for each sites and stores them into a txt file. normalized variable on line 44 determines if we want to normalize each inidviual bearing to have a sum of 1. 
- *positionCalculation.py* - Load bearing txt files into memory and calculate and sotre positions into *position_non_normalized* table. The likelihood of the position and the number of sites used in the calculation are also being recorded. 
- *numberOfPositionVsThreshold.py* - Plot the likelihood threshold vs number of positons.
- *positionPlots.py* -  Plot easting and northing according to the settings. Change DeploymentID, normalized, and likelihood variables on line 108, 110, and 111 to plot with differnet settings. 
- *qraatSignal* - My modification of the Singal module from QRAAT system to run on my own environment. 


**Tables:**

- *position_non_normalized* – stores the calculated positions with their likelihood and number of site used.


```
CREATE TABLE IF NOT EXISTS qraat.`position_non_normalized` (
`ID` int(10) unsigned NOT NULL AUTO_INCREMENT, 
`deploymentID` int(10) unsigned NOT NULL,
`timestamp` decimal(16,6) NOT NULL, 
`easting` decimal(9,2) NOT NULL, 
`northing` decimal(10,2) NOT NULL,
`likelihood` decimal(10,9) NOT NULL,
`numSites` int(10) unsigned NOT NULL,
`isNormalized` boolean NOT NULL,
PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

```
