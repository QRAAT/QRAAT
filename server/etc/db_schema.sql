
SET GLOBAL innodb_file_per_table=1;

-- Site
CREATE TABLE IF NOT EXISTS qraat.`site` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) DEFAULT NULL,
  `location` varchar(100) DEFAULT NULL,
  `latitude` decimal(10,6) DEFAULT NULL,
  `longitude` decimal(11,6) DEFAULT NULL,
  `easting` decimal(9,2) unsigned DEFAULT '0.00',
  `northing` decimal(10,2) unsigned DEFAULT '0.00',
  `utm_zone_number` tinyint(3) unsigned DEFAULT '10',
  `utm_zone_letter` char(1) DEFAULT 'S',
  `elevation` decimal(7,2) DEFAULT '0.00',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB;


-- Project
CREATE TABLE IF NOT EXISTS qraat.`project` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `ownerID` int(10) unsigned NOT NULL COMMENT 'References UUID in web frontend, i.e. `django.auth_user.id`.',
  `name` varchar(50) NOT NULL,
  `description` text,
  `is_public` tinyint(1) NOT NULL,
  `is_hidden` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qraat.`auth_project_viewer` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `groupID` int(10) unsigned NOT NULL COMMENT 'References GUID in web frontend, i.e. `django.auth_group.id`.',
  `projectID` int(10) unsigned NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `projectID` (`projectID`),
  UNIQUE KEY (`groupID`, `projectID`), 
  CONSTRAINT `auth_project_viewer_ibfk_1` FOREIGN KEY (`projectID`) REFERENCES `project` (`ID`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qraat.`auth_project_collaborator` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `groupID` int(10) unsigned NOT NULL COMMENT 'References GUID in web frontend, i.e. `django.auth_group.id`.',
  `projectID` int(10) unsigned NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `projectID` (`projectID`),
  UNIQUE KEY (`groupID`, `projectID`), 
  CONSTRAINT `auth_project_collaborator_ibfk_1` FOREIGN KEY (`projectID`) REFERENCES `project` (`ID`)
) ENGINE=InnoDB;


-- Transmitter
CREATE TABLE IF NOT EXISTS qraat.`tx` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `serial_no` varchar(50) NOT NULL,
  `tx_makeID` int(10) unsigned NOT NULL,
  `projectID` int(10) unsigned NOT NULL COMMENT 'Project for which transmitter was originally created.',
  `frequency` double NOT NULL,
  `is_hidden` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`ID`),
  KEY `projectID` (`projectID`),
  CONSTRAINT `tx_ibfk_1` FOREIGN KEY (`projectID`) REFERENCES `project` (`ID`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qraat.`tx_make` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `manufacturer` varchar(50) DEFAULT NULL,
  `model` varchar(50) DEFAULT NULL,
  `demod_type` enum('pulse','cont','afsk') DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qraat.`tx_parameters` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `txID` int(10) unsigned NOT NULL,
  `name` varchar(32) NOT NULL,
  `value` varchar(64) NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `txID` (`txID`),
  KEY `name` (`name`),
  CONSTRAINT `tx_parameters_ibfk_1` FOREIGN KEY (`txID`) REFERENCES `tx` (`ID`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qraat.`tx_make_parameters` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `tx_makeID` int(10) unsigned NOT NULL,
  `name` varchar(32) NOT NULL,
  `value` varchar(64) NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `tx_makeID` (`tx_makeID`),
  KEY `name` (`name`),
  CONSTRAINT `tx_make_parameters_ibfk_1` FOREIGN KEY (`tx_makeID`) REFERENCES `tx_make` (`ID`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qraat.`afsk` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `deploymentID` int(10) unsigned DEFAULT NULL,
  `siteID` int(10) unsigned DEFAULT NULL,
  `start_timestamp` decimal(16,6) DEFAULT NULL COMMENT 'Unix Timestamp (s.us)',
  `stop_timestamp` decimal(16,6) DEFAULT NULL COMMENT 'Unix Timestamp (s.us)',
  `message` varchar(50) DEFAULT NULL,
  `binary_data` varbinary(63) DEFAULT NULL,
  `error` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM ;

-- Target
CREATE TABLE IF NOT EXISTS qraat.`target` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `description` text,
  `projectID` int(10) unsigned NOT NULL COMMENT 'Project for which target was originally created.',
  `is_hidden` tinyint(1) DEFAULT '0',
  `max_speed_family` ENUM('exp', 'linear', 'const'), 
  `speed_burst` double DEFAULT NULL, 
  `speed_sustained` double DEFAULT NULL, 
  `speed_limit` double NOT NULL, 
  PRIMARY KEY (`ID`),
  KEY `projectID` (`projectID`),
  CONSTRAINT `target_ibfk_1` FOREIGN KEY (`projectID`) REFERENCES `project` (`ID`)
) ENGINE=InnoDB;


-- Project Locations
CREATE TABLE IF NOT EXISTS qraat.`location` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `projectID` int(10) unsigned NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `description` text,
  `location` varchar(100) DEFAULT NULL,
  `latitude` decimal(10,6) DEFAULT NULL,
  `longitude` decimal(11,6) DEFAULT NULL,
  `easting` decimal(9,2) unsigned DEFAULT '0.00',
  `northing` decimal(10,2) unsigned DEFAULT '0.00',
  `utm_zone_number` tinyint(3) unsigned DEFAULT '10',
  `utm_zone_letter` char(1) DEFAULT 'S',
  `elevation` decimal(7,2) DEFAULT '0.00',
  `is_hidden` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`ID`),
  KEY `projectID` (`projectID`),
  CONSTRAINT `location_ibfk_1` FOREIGN KEY (`projectID`) REFERENCES `project` (`ID`)
) ENGINE=InnoDB;


-- Deployment
CREATE TABLE IF NOT EXISTS qraat.`deployment` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `description` text,
  `time_start` decimal(16,6) DEFAULT NULL COMMENT 'Unix Timestamp (s.us)',
  `time_end` decimal(16,6) DEFAULT NULL COMMENT 'Unix Timestamp (s.us)',
  `txID` int(10) unsigned NOT NULL,
  `targetID` int(10) unsigned NOT NULL,
  `projectID` int(10) unsigned NOT NULL COMMENT 'Project to which deployment is associated.',
  `is_active` tinyint(1) DEFAULT '0',
  `is_hidden` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`ID`),
  KEY `txID` (`txID`),
  KEY `targetID` (`targetID`),
  KEY `projectID` (`projectID`),
  CONSTRAINT `deployment_ibfk_1` FOREIGN KEY (`txID`) REFERENCES `tx` (`ID`),
  CONSTRAINT `deployment_ibfk_2` FOREIGN KEY (`targetID`) REFERENCES `target` (`ID`),
  CONSTRAINT `deployment_ibfk_3` FOREIGN KEY (`projectID`) REFERENCES `project` (`ID`)
) ENGINE=InnoDB;


-- EST
CREATE TABLE IF NOT EXISTS qraat.`est` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `siteID` int(10) unsigned DEFAULT NULL,
  `timestamp` decimal(16,6) DEFAULT NULL COMMENT 'Unix Timestamp (s.us)',
  `frequency` int(11) DEFAULT NULL COMMENT 'Tag Frequency (Hz)',
  `center` int(11) DEFAULT NULL COMMENT 'Band Center Frequency (Hz)',
  `fdsp` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal Power',
  `fd1r` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 1 - real part',
  `fd1i` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 1 - imaginary part',
  `fd2r` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 2 - real part',
  `fd2i` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 2 - imaginary part',
  `fd3r` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 3 - real part',
  `fd3i` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 3 - imaginary part',
  `fd4r` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 4 - real part',
  `fd4i` double DEFAULT NULL COMMENT 'Fourier Decomposition Signal on Channel 4 - imaginary part',
  `band3` smallint(6) DEFAULT NULL COMMENT ' ',
  `band10` smallint(6) DEFAULT NULL COMMENT '10dB Bandwidth',
  `edsp` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal Power',
  `ed1r` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 1 - real part',
  `ed1i` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 1 - imaginary part',
  `ed2r` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 2 - real part',
  `ed2i` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 2 - imaginary part',
  `ed3r` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 3 - real part',
  `ed3i` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 3 - imaginary part',
  `ed4r` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 4 - real part',
  `ed4i` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition Signal on Channel 4 - imaginary part',
  `ec` double DEFAULT NULL COMMENT 'Eigenvalue Confidence',
  `tnp` double DEFAULT NULL COMMENT 'Total Noise Power',
  `nc11r` double DEFAULT NULL COMMENT 'Noise Covariance 11 - real part',
  `nc11i` double DEFAULT NULL COMMENT 'Noise Covariance 11 - imaginary part',
  `nc12r` double DEFAULT NULL COMMENT 'Noise Covariance 12 - real part',
  `nc12i` double DEFAULT NULL COMMENT 'Noise Covariance 12 - imaginary part',
  `nc13r` double DEFAULT NULL COMMENT 'Noise Covariance 13 - real part',
  `nc13i` double DEFAULT NULL COMMENT 'Noise Covariance 13 - imaginary part',
  `nc14r` double DEFAULT NULL COMMENT 'Noise Covariance 14 - real part',
  `nc14i` double DEFAULT NULL COMMENT 'Noise Covariance 14 - imaginary part',
  `nc21r` double DEFAULT NULL COMMENT 'Noise Covariance 21 - real part',
  `nc21i` double DEFAULT NULL COMMENT 'Noise Covariance 21 - imaginary part',
  `nc22r` double DEFAULT NULL COMMENT 'Noise Covariance 22 - real part',
  `nc22i` double DEFAULT NULL COMMENT 'Noise Covariance 22 - imaginary part',
  `nc23r` double DEFAULT NULL COMMENT 'Noise Covariance 23 - real part',
  `nc23i` double DEFAULT NULL COMMENT 'Noise Covariance 23 - imaginary part',
  `nc24r` double DEFAULT NULL COMMENT 'Noise Covariance 24 - real part',
  `nc24i` double DEFAULT NULL COMMENT 'Noise Covariance 24 - imaginary part',
  `nc31r` double DEFAULT NULL COMMENT 'Noise Covariance 31 - real part',
  `nc31i` double DEFAULT NULL COMMENT 'Noise Covariance 31 - imaginary part',
  `nc32r` double DEFAULT NULL COMMENT 'Noise Covariance 32 - real part',
  `nc32i` double DEFAULT NULL COMMENT 'Noise Covariance 32 - imaginary part',
  `nc33r` double DEFAULT NULL COMMENT 'Noise Covariance 33 - real part',
  `nc33i` double DEFAULT NULL COMMENT 'Noise Covariance 33 - imaginary part',
  `nc34r` double DEFAULT NULL COMMENT 'Noise Covariance 34 - real part',
  `nc34i` double DEFAULT NULL COMMENT 'Noise Covariance 34 - imaginary part',
  `nc41r` double DEFAULT NULL COMMENT 'Noise Covariance 41 - real part',
  `nc41i` double DEFAULT NULL COMMENT 'Noise Covariance 41 - imaginary part',
  `nc42r` double DEFAULT NULL COMMENT 'Noise Covariance 42 - real part',
  `nc42i` double DEFAULT NULL COMMENT 'Noise Covariance 42 - imaginary part',
  `nc43r` double DEFAULT NULL COMMENT 'Noise Covariance 43 - real part',
  `nc43i` double DEFAULT NULL COMMENT 'Noise Covariance 43 - imaginary part',
  `nc44r` double DEFAULT NULL COMMENT 'Noise Covariance 44 - real part',
  `nc44i` double DEFAULT NULL COMMENT 'Noise Covariance 44 - imaginary part',
  `fdsnr` double DEFAULT NULL COMMENT 'Fourier Decomposition SNR (dB)',
  `edsnr` double DEFAULT NULL COMMENT 'Eigenvalue Decomposition SNR (dB)',
  `deploymentID` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `timestamp` (`timestamp`),
  KEY `siteid` (`siteID`),
  KEY `deploymentID` (`deploymentID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`estscore` (
  `estID` bigint(20) unsigned NOT NULL DEFAULT '0',
  `score` int(11) NOT NULL COMMENT 'Number of coroborating pulses or flagged as bad (negative).',
  `max_score` int(11) NOT NULL COMMENT 'Maximum score over pulse score neighborhood.',
  `theoretical_score` int(11) NOT NULL COMMENT 'Optimal score over score interval.',
  PRIMARY KEY (`estID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`estinterval` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `deploymentID` int(10) unsigned NOT NULL,
  `siteID` int(10) unsigned NOT NULL,
  `timestamp` decimal(16,6) NOT NULL COMMENT 'Start of interval.',
  `duration` double NOT NULL COMMENT 'Duration of the interval in seconds.',
  `pulse_interval` double DEFAULT NULL COMMENT 'Estimated pulse rate of the transmitter in seconds (mode).',
  `pulse_variation` double DEFAULT NULL COMMENT 'Measurement of varition of the pulse rate (second moment).',
  PRIMARY KEY (`ID`),
  KEY (`deploymentID`,`siteID`, `timestamp`)
) ENGINE=MyISAM;


-- Telemetry
CREATE TABLE IF NOT EXISTS qraat.`telemetry` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `siteID` int(10) unsigned NOT NULL,
  `timestamp` decimal(16,6) DEFAULT NULL,
  `datetime` datetime DEFAULT NULL,
  `timezone` varchar(6) DEFAULT NULL,
  `intemp` decimal(4,2) DEFAULT NULL,
  `extemp` decimal(4,2) DEFAULT NULL,
  `voltage` decimal(4,2) DEFAULT NULL,
  `ping_power` int(11) DEFAULT NULL,
  `ping_computer` int(11) DEFAULT NULL,
  `site_status` int(11) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`timecheck` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `siteID` bigint(10) unsigned NOT NULL,
  `timestamp` decimal(16,6) DEFAULT NULL,
  `datetime` datetime DEFAULT NULL,
  `timezone` varchar(6) DEFAULT NULL,
  `time_offset` decimal(10,3) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`detcount` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `siteID` int(10) unsigned NOT NULL,
  `datetime` datetime DEFAULT NULL,
  `timezone` varchar(6) DEFAULT NULL,
  `server` int(11) DEFAULT NULL,
  `site` int(11) DEFAULT NULL,
  `timestamp` decimal(16,6) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`estcount` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `siteID` int(10) unsigned NOT NULL,
  `datetime` datetime DEFAULT NULL,
  `timezone` varchar(6) DEFAULT NULL,
  `server` int(11) DEFAULT NULL,
  `site` int(11) DEFAULT NULL,
  `timestamp` decimal(16,6) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`procount` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `siteID` int(10) unsigned NOT NULL,
  `datetime` datetime DEFAULT NULL,
  `timezone` varchar(6) DEFAULT NULL,
  `estserver` int(11) DEFAULT NULL,
  `festserver` int(11) DEFAULT NULL,
  `timestamp` decimal(16,6) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;


-- Calibration
CREATE TABLE IF NOT EXISTS qraat.`calibration_information` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `description` text,
  `deploymentID` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`gps_data` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `deploymentID` int(10) unsigned DEFAULT NULL,
  `timestamp` int(11) DEFAULT NULL,
  `latitude` decimal(10,6) DEFAULT NULL,
  `longitude` decimal(11,6) DEFAULT NULL,
  `elevation` decimal(7,2) DEFAULT NULL,
  `easting` decimal(9,2) DEFAULT NULL,
  `northing` decimal(10,2) DEFAULT NULL,
  `utm_zone_number` tinyint(3) unsigned DEFAULT '10',
  `utm_zone_letter` char(1) DEFAULT 'S',
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`true_position` (
  `estID` bigint(20) unsigned NOT NULL,
  `easting` decimal(9,2) DEFAULT NULL,
  `northing` decimal(10,2) DEFAULT NULL,
  `bearing` decimal(5,2) DEFAULT NULL,
  PRIMARY KEY (`estID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`steering_vectors` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `cal_infoID` int(10) unsigned DEFAULT NULL,
  `siteID` int(10) unsigned DEFAULT NULL,
  `bearing` decimal(5,2) DEFAULT NULL,
  `sv1r` double DEFAULT NULL,
  `sv1i` double DEFAULT NULL,
  `sv2r` double DEFAULT NULL,
  `sv2i` double DEFAULT NULL,
  `sv3r` double DEFAULT NULL,
  `sv3i` double DEFAULT NULL,
  `sv4r` double DEFAULT NULL,
  `sv4i` double DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;


-- Position
CREATE TABLE IF NOT EXISTS qraat.`bearing` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `deploymentID` int(10) unsigned DEFAULT NULL,
  `siteID` int(10) unsigned NOT NULL,
  `timestamp` decimal(16,6) NOT NULL,
  `bearing` double NOT NULL COMMENT 'Most likely bearing, not interpolated. [0,360) degrees',
  `likelihood` double NOT NULL COMMENT 'Normalized likelihood of most likely bearing. [0,1]',
  `activity` double DEFAULT NULL COMMENT 'Normalized activity metric. [0,1]',
  `number_est_used` int(10) unsigned DEFAULT NULL COMMENT 'Number of contributing est records.',
  PRIMARY KEY (`ID`),
  KEY `timestamp` (`timestamp`),
  KEY `deploymentID` (`deploymentID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`position` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `deploymentID` int(10) unsigned DEFAULT NULL,
  `timestamp` decimal(16,6) NOT NULL,
  `latitude` decimal(10,6) DEFAULT NULL,
  `longitude` decimal(11,6) DEFAULT NULL,
  `easting` decimal(9,2) NOT NULL COMMENT 'Most likely position (UTM east).',
  `northing` decimal(10,2) NOT NULL COMMENT 'Most likely position (UTM north).',
  `utm_zone_number` tinyint(3) unsigned DEFAULT 10 COMMENT 'Most likely position (UTM zone).',
  `utm_zone_letter` varchar(1) DEFAULT 'S' COMMENT 'Most likely position (UTM zone letter).',
  `likelihood` double NOT NULL COMMENT 'Normalized likelihood value at most likely position. [0,1]',
  `activity` double DEFAULT NULL COMMENT 'Averaged over bearing data from all sites. [0,1]',
  `number_est_used` int(10) unsigned DEFAULT NULL COMMENT 'Number of contributing est records.',
  PRIMARY KEY (`ID`),
  KEY `timestamp` (`timestamp`),
  KEY `deploymentID` (`deploymentID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`covariance` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `positionID` bigint(20) unsigned DEFAULT NULL,
  `status` enum('ok', 'nonposdef', 'singular', 'undefined') NOT NULL, 
  `method` enum('boot','boot2') DEFAULT 'boot',
  `cov11` double DEFAULT NULL,
  `cov12` double DEFAULT NULL,
  `cov21` double DEFAULT NULL,
  `cov22` double DEFAULT NULL, 
  `lambda1` double DEFAULT NULL COMMENT 'Large eigenvalue of covariance matrix.', 
  `lambda2` double DEFAULT NULL COMMENT 'Small eigenvalue of covariance matrix.', 
  `alpha` double DEFAULT NULL COMMENT 'Orientation of major axis of ellipse.', 
  `w99` double DEFAULT NULL COMMENT 'Mahalonobis distance, 99.7%-confidence.',
  `w95` double DEFAULT NULL COMMENT 'Mahalonobis distance, 95%-confidence.',
  `w90` double DEFAULT NULL COMMENT 'Mahalonobis distance, 90%-confidence.',
  `w80` double DEFAULT NULL COMMENT 'Mahalonobis distance, 80%-confidence.',
  `w68` double DEFAULT NULL COMMENT 'Mahalonobis distance, 68%-confidence.',
  PRIMARY KEY (`ID`),
  KEY `positionID` (`positionID`)
) ENGINE=MyISAM;


-- Tracks
CREATE TABLE IF NOT EXISTS qraat.`track_pos` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `positionID` bigint(20) unsigned DEFAULT NULL,
  `deploymentID` int(10) unsigned NOT NULL DEFAULT '0',
  `timestamp` decimal(16,6) NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `deploymentID` (`deploymentID`,`timestamp`)
) ENGINE=MyISAM;


CREATE TABLE IF NOT EXISTS qraat.`provenance` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `obj_table` varchar(30) NOT NULL,
  `obj_id` bigint(20) unsigned NOT NULL,
  `dep_table` varchar(30) NOT NULL,
  `dep_id` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;


-- Processing
CREATE TABLE IF NOT EXISTS qraat.`processing_cursor` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `value` bigint(20) unsigned NOT NULL,
  `name` varchar(20) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`processing_statistics` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `timestamp` int(10) unsigned NOT NULL,
  `duration` double unsigned,
  `process` varchar(100) NOT NULL,
  `beginning_timestamp` decimal(16,6) DEFAULT NULL,
  `ending_timestamp` decimal(16,6) DEFAULT NULL,
  `beginning_index` bigint(20) unsigned DEFAULT NULL,
  `ending_index` bigint(20) unsigned DEFAULT NULL,
  `number_records_input` int(10) unsigned DEFAULT NULL,
  `number_records_output` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;


-- Archiving
CREATE TABLE IF NOT EXISTS qraat.`archive_log` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `timestamp` decimal(16,6) NOT NULL COMMENT 'Time at which the table (chunk) was archived',
  `filename` varchar(100) NOT NULL COMMENT 'Filename for the table (chunk)',
  `tablename` varchar(30) NOT NULL COMMENT 'Name of the archived table',
  `startid` bigint(20) unsigned NOT NULL COMMENT 'First ID of the records written to the file',
  `finishid` bigint(20) unsigned NOT NULL COMMENT 'Last ID of the records written to the file',
  `mindt` datetime DEFAULT NULL COMMENT 'Earliest datetime of all records in chunk, if datetime exists',
  `maxdt` datetime DEFAULT NULL COMMENT 'Latest datetime of all records in chunk, if datetime exists',
  `mints` decimal(16,6) DEFAULT NULL COMMENT 'Earliest timestamp of all records in chunk, if timestamp exists',
  `maxts` decimal(16,6) DEFAULT NULL COMMENT 'Latest timestamp of all records in chunk, if timestamp exists',
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

CREATE TABLE IF NOT EXISTS qraat.`archive_config` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `tablename` varchar(100) DEFAULT NULL COMMENT 'The name of the table to be archived',
  `archive` tinyint(1) DEFAULT '0' COMMENT 'Set to 1 to archive this table, 0 to ignore this table',
  `lastid` bigint(20) unsigned DEFAULT NULL COMMENT 'Set to the ID of the last archived record',
  `chunk` int(11) DEFAULT NULL COMMENT 'Maximum size of a chunk, in records, 0 to disable chunking',
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM;

-- Configuration information for MoveBank export jobs. See Gene.
CREATE TABLE IF NOT EXISTS qraat.`movebank_export`(
	`ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
	`deploymentID` int(10) unsigned NOT NULL,
	`time_last_export` decimal(16,6) NOT NULL,
	`export_interval` int(10) unsigned NOT NULL,
	`studyID` varchar(20) NOT NULL,
	`formatID` varchar(20) NOT NULL,	
	`enable` tinyint(1) NOT NULL,
	PRIMARY KEY (`ID`),
	KEY `deploymentID` (`deploymentID`)
) ENGINE=MyISAM;
