<?php

	// Global variables and code
	// A list of decent color codes for each trace
	$Coltab = array
	(	// ABGR	(alpha/transparency,blue,green,red)
		"990000FF",	// 
		"9900FF00",	// 
		"99FF0000",	// 
		"9900FFFF",	// 
		"99FF00FF",	// 
		"99FFFF00",	// 
		"990000CC",	// 
		"9900CC00",	// 
		"99CC0000",	// 
		"9900CCCC",	// 
		"99CC00CC",	// 
		"99CCCC00",	// 
		"99000099",	// 
		"99000099",	// 
		"99009900",	// 
		"99990000",	// 
		"99009999",	// 
		"99990099",	// 
		"99999900",	// 
		"99000066",	// 
		"99006600",	// 
		"99660000",	// 
		"99006666",	// 
		"99660066",	// 
		"99666600",	// 
		"99000033",	// 
		"99003300",	// 
		"99330000",	// 
		"99003333",	// 
		"99330033",	// 
		"99333300",	// 
	) ;
	$TmpDirectory = "tmp/" ;	// Write KML file to tmp subdirectory
	$KMLURL = "http://localhost/rmg/".$TmpDirectory ;	// URL to KML file, returned to client
	date_default_timezone_set('America/Los_Angeles') ;
	error_reporting(E_ALL) ;
	$ufi = rand(1000,10000) ;				// 4 digit random number, used as a User File Identifier, or ufi
	$debugfilename = "tmp/debug".$ufi.".txt" ;		// create a filename that is only used for this request
	$debugfile = fopen($debugfilename,"w") ;
	debug("=== start\n") ;
	main($ufi) ;
	debug("=== finish\n") ;
	if( $debugfile ) fclose($debugfile) ;
	return 0 ;

	function main($ufi)
	{
		//
		// Gather input parameters: start, stop, options
		//
		$start = "" ;
		if( isset($_REQUEST["start"]) )
		{
			$start = $_REQUEST["start"];
		}
		if( $start == "" )
		{
			debug("Missing value for parameter start\n") ;
			print "ERROR: Missing value for parameter start\n" ;
			return FALSE ;
		}
		debug("Start=$start\n") ;
		//
		$stop = "" ;
		if( isset($_REQUEST["stop"]) )
		{
			$stop = $_REQUEST["stop"];
		}
		if( $stop == "" )
		{
			debug("Missing value for parameter stop\n") ;
			print "ERROR: Missing value for parameter stop\n" ;
			return FALSE ;
		}
		debug("Stop=$stop\n") ;
		//
		$options = "" ;
		if( isset($_REQUEST["options"]) )
		{
			$options = $_REQUEST["options"];
		}
		if( $options == "" )
		{
			debug("Missing value for parameter options\n") ;
			print "ERROR: Missing value for parameter options\n" ;
			return FALSE ;
		}
		debug("Options=$options\n") ;
		//
		$track = "" ;
		if( isset($_REQUEST["track"]) )
		{
			$track = $_REQUEST["track"];
		}
		if( $track == "" )
		{
			debug("Missing value for parameter track\n") ;
			print "ERROR: Missing value for parameter track\n" ;
			return FALSE ;
		}
		debug("Track=$track\n") ;
		if( $track == "All" )
		{
			$query = "SELECT * from track WHERE datetime between '$start' and '$stop' ORDER BY transmitter, datetime ASC ;" ;
		}
		else
		{
			$query = "SELECT * from track WHERE datetime between '$start' and '$stop' and transmitter like '$track' ORDER BY transmitter, datetime ASC ;" ;
		}
		$trackdata = getdata($query) ;
		if( count($trackdata) < 1 )
		{
			debug("Read no track data\n") ;
			print "ERROR: No track data\n" ;
			return FALSE ;
		}
		$entries = count($trackdata) ;
		debug("Got $entries of track data\n") ;
		// makeup a kml filename
		$kmlfilename = $ufi.".kml" ;
		writekmlfile($trackdata,$start,$stop,$kmlfilename,$options) ;	// writes a KML file, returns TRUE for OK, FALSE for error
		print "OK\nFilename=$kmlfilename\n" ;
		return TRUE ;
	}

	function getdata($query)
	{
		include("dbcredentials.php") ; // Sets $hostname,$username,$password,$database
		$dbc = mysql_connect($hostname,$username,$password) ;
		if( !$dbc )
		{
			debug("Could not connect to database: ".mysql_error()."\n") ;
			return NULL ;
		}
		mysql_select_db($database,$dbc) ;
		//$query = mysql_real_escape_string($query,$dbc) ;
		debug("Query=$query\n") ;
		$result = mysql_query($query,$dbc) ;
		$numrows = @mysql_numrows($result) ;
		$data = array() ;
		while ($numrows-- > 0 )
		{
			$row = mysql_fetch_row($result) ;
			$data[] = $row ;	// Add each row of table data to the two dimensional array data
		}
		mysql_close($dbc) ;
		return $data ;
	}

	function writekmlfile($trackdata,$start,$stop,$filename,$options)	// writes a KML file, returns TRUE for OK, FALSE for error
	{
		//global $trackdata ;	// the tracking data
		global $KMLURL ;	// the URL for the KML
		global $TmpDirectory ;	// the subdir to write the KML
		//
		// Read options and break out into flags
		//
		// from formcontrols.js: showtrace+coloreach+markstart+markend
		// local names for this: optiontrace,optionunique,optionmarkstart,optionmarkend
		$optiontrace = false ;
		$optionunique = false ;
		$optionmarkstart = false ;
		$optionmarkend = false ;
		if( substr($options,0,1) == "Y" )
		{
			$optiontrace = true ;
		}
		if( substr($options,1,1) == "Y" )
		{
			$optionunique = true ;
		}
		if( substr($options,2,1) == "Y" )
		{
			$optionmarkstart = true ;
		}
		if( substr($options,3,1) == "Y" )
		{
			$optionmarkend = true ;
		}
		debug("options: trace=".$optiontrace." unique=".$optionunique." markstart=".$optionmarkstart." markend=".$optionmarkend."\n") ;
		$numberoflines = count($trackdata) ;
		debug("numberoflines=$numberoflines\n") ;
		//
		// Open KML file for writing
		//
		$fd = fopen($TmpDirectory.$filename,"w") ;	// open KML file
		if( !$fd )
		{
			debug("Error creating KML file\n") ;
			print "ERROR: Error creating KML file\n" ;
			return FALSE ;
		}
		//
		//	Structure of KML file
		//	KML header
		//		Track 1 Start Marker
		//		Trace 1 Header
		//			Trace 1 Point 1
		//			...
		//			Trace 1 Point N
		//		Trace 1 Footer
		//		Track 1 Stop Marker
		//		..
		//		Track N Start Marker
		//		Trace N Header
		//			Trace N Point 1
		//			...
		//			Trace N Point N
		//		Trace N Footer
		//		Track N Stop Marker
		//	KML footer
		//
		debug("writing kml file '".$filename."'\n") ;
		write_Kml_Header($fd,$start,$stop) ;
		$startmarker = "http://maps.google.com/mapfiles/kml/pal4/icon56.png" ;	// set start marker to white square
		$endmarker = "http://maps.google.com/mapfiles/kml/pal4/icon57.png" ;	// set end marker to white circle
		$lasttrackname = "" ;
		$lasttracktime = "" ;
		$lasttracklon = "" ;
		$lasttracklat = "" ;
		$trackcount = 0 ;
		for( $line = 0 ; $line < $numberoflines ; $line++ )
		{
			$linedata = $trackdata[$line] ;
			$tracktime = $linedata[1]." ".$linedata[2] ;
			$trackname = $linedata[3] ;
			$tracklat = $linedata[4] ;
			$tracklon = $linedata[5] ;
			$trackflag = $linedata[6] ;
			if( $lasttrackname != $trackname )	// Transition to a new track
			{
				$trackcount++ ;
				//
				// Terminate the previous track
				if( $lasttrackname != "" )	// If this is not the first line of track data
				{
					// Trace N-1 Footer
					if( $optiontrace )	// if optiontrace is set, close trace
					{
						write_Trace_Footer($fd) ;
					}
					//
					// Trace N-1 Stop Marker
					if( $optionmarkend )	// if optionmarkend is set, add a marker for the track endpoint
					{
						write_Track_Marker($fd,$lasttrackname." end point",$lasttracktime,$lasttracklon,$lasttracklat,$endmarker) ;
					}
				}
				//
				// Start a new track
				// Write a start marker
				if( $optionmarkstart )	// if optionmarkstart is set, add a marker for the track startpoint
				{
					write_Track_Marker($fd,$trackname." start point",$tracktime,$tracklon,$tracklat,$startmarker) ; //	Write the track start position
				}
				//
				// Start a new trace
				if( $optiontrace )				// if optiontrace is set, output trace placemarker
				{
					// Figure out the color
					$colorindex = 1 ;	// default color
					if( $optionunique )	// if optionunique is set, change color for each track
					{
						$colorindex = crc32($trackname) ;	// Easy way to link color to name
					}
					$colorcode = colorcodelookup($colorindex) ;
					debug("colorcode=".$colorcode."\n") ;
					write_Trace_Start($fd,$trackname,$colorcode) ;
				}
				//
				// Start the trace at the start marker
				if( $optiontrace )			// if optiontrace is set, output trace point
				{
					write_Trace_Point($fd,$tracklon,$tracklat) ;
				}
			}
			else	// if( $lasttrackname != $trackname )	// Transition to a new track
			{
				// Continue a previous track
				if( $optiontrace )			// if optiontrace is set, output trace point
				{
					write_Trace_Point($fd,$tracklon,$tracklat) ;
				}
			}
			$lasttracktime = $tracktime ;
			$lasttrackname = $trackname ;
			$lasttracklat = $tracklat ;
			$lasttracklon = $tracklon ;
		}
		// Finish the trace and track in progress
		if( $lasttrackname != "" )	// If this is not the first line of track data
		{
			// Trace N Footer
			if( $optiontrace )	// if optiontrace is set, close trace
			{
				write_Trace_Footer($fd) ;
			}
			//
			// Trace N Stop Marker
			if( $optionmarkend )	// if optionmarkend is set, add a marker for the track endpoint
			{
				write_Track_Marker($fd,$lasttrackname." end point",$lasttracktime,$lasttracklon,$lasttracklat,$endmarker) ;
			}
		}
		write_Kml_Footer($fd) ;
		fclose($fd) ;
		debug("finished writing kml file\n") ;
		return TRUE ;
	}

	function write_Kml_Header($fd,$start,$stop)
	{
		fwrite($fd,'<?xml version="1.0" encoding="UTF-8"?>'."\n") ;
		//fwrite($fd,'<kml xmlns="http://earth.google.com/kml/2.0">'."\n") ;
		fwrite($fd,'<kml xmlns="http://www.opengis.net/kml/2.2">'."\n") ;
		fwrite($fd,' <Document>'."\n") ;
		fwrite($fd,'  <name>Tracking data file generated by RMG.</name>'."\n") ;
		fwrite($fd,'  <description>'."\n") ;
		fwrite($fd,'These tracks are simulated. ') ;
		fwrite($fd,'The time period starts at '.$start.', stops at '.$stop."\n") ;
		fwrite($fd,'  </description>'."\n") ;
	}

	function write_Kml_Footer($fd)
	{
		fwrite($fd,' </Document>'."\n") ;
		fwrite($fd,'</kml>'."\n") ;
	}

	function write_Track_Marker($fd,$trackname,$tracktime,$tracklon,$tracklat,$iconurl)
	{
		fwrite($fd,'  <Placemark>'."\n") ;
		fwrite($fd,'   <name>Track '.$trackname.'</name>'."\n") ;
		fwrite($fd,'   <description>'.$tracktime.'</description>'."\n") ;
		fwrite($fd,'   <Style>'."\n") ;
		fwrite($fd,'    <IconStyle>'."\n") ;
		fwrite($fd,'     <Icon><href>'.$iconurl.'</href></Icon>'."\n") ;
		fwrite($fd,'    </IconStyle>'."\n") ;
		fwrite($fd,'   </Style>'."\n") ;
		fwrite($fd,'   <Point>'."\n") ;
		$pointstring = sprintf("%.6f,%.6f,0",$tracklon,$tracklat) ;
		fwrite($fd,'    <coordinates>') ;
		fwrite($fd,$pointstring) ;
		fwrite($fd,'</coordinates>'."\n") ;
		fwrite($fd,'   </Point>'."\n") ;
		fwrite($fd,'  </Placemark>'."\n") ;
	}

	function write_Trace_Start($fd,$trackname,$colorcode)
	{
		fwrite($fd,'  <Placemark>'."\n") ;
		fwrite($fd,'   <name>Track '.$trackname.'</name>'."\n") ;
		fwrite($fd,'   <description>This is the trace for track '.$trackname.'</description>'."\n") ;
		fwrite($fd,'   <Style>'."\n") ;
		fwrite($fd,'    <LineStyle>'."\n") ;
		fwrite($fd,'     <color>'.$colorcode.'</color>'."\n") ;
		fwrite($fd,'     <width>4</width>'."\n") ;
		fwrite($fd,'    </LineStyle>'."\n") ;
		fwrite($fd,'   </Style>'."\n") ;
		fwrite($fd,'   <LineString>'."\n") ;
		fwrite($fd,'    <coordinates>') ;		// To Be Continued ...
	}

	function write_Trace_Point($fd,$tracklon,$tracklat)	// ...here...
	{
		$pointstring = sprintf("%.6f,%.6f,0 ",$tracklon,$tracklat) ;
		fwrite($fd,$pointstring) ;	// write this position to the KML output file
	}

	function write_Trace_Footer($fd)			// ... and here
	{
		fwrite($fd,"\n") ;
		fwrite($fd,'    </coordinates>'."\n") ;
		fwrite($fd,'   </LineString>'."\n") ;
		fwrite($fd,'  </Placemark>'."\n") ;
	}

	function colorcodelookup($index)
	{
		global $Coltab ;
		$length = count($Coltab) ;
		if( $index < 0 )
		{
			$index = -$index ;
		}
		$index = $index % $length ;
		return $Coltab[$index] ;
	}

	function debug($string)
	{
		global $debugfile ;
		if( $debugfile )
		{
			$timestamp = date(DATE_RFC822) ;
			fwrite($debugfile,$timestamp.": ".$string) ;
		}
	}

?>
