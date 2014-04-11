<?php
	// Global code
	$givenstart = "" ;
	$givenstop = "" ;
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
		// Gather input parameters
		//
		global $givenstart ;
		global $givenstop ;
		$type = "" ;
		if( isset($_REQUEST["type"]) )
		{
			$type = $_REQUEST["type"];
		}
		if( $type == "" )
		{
			debug("Missing value for parameter type\n") ;
			print "ERROR: Missing value for parameter type\n" ;
			return FALSE ;
		}
                if( $type == "extent" )
                {
                        debug("Command extent\n") ;
                        return extent() ;
                }
                if( $type == "tracklist" )
                {
                        debug("Command tracklist\n") ;
                        return tracklist() ;
                }
		//
		if( isset($_REQUEST["givenstart"]) )
		{
			$givenstart = $_REQUEST["givenstart"];
		}
		if( $givenstart != "" )
		{
			debug("givenstart defined\n") ;
		}
		//
		if( isset($_REQUEST["givenstop"]) )
		{
			$givenstop = $_REQUEST["givenstop"];
		}
		if( $givenstop != "" )
		{
			debug("givenstop defined\n") ;
		}
		debug("Unknown input parameter '$type'\n") ;
		print "Unknown input parameter '$type'\n" ;
		return FALSE ;
	}

	function dblookup($query)
	{
		include("dbcredentials.php") ; // Sets $hostname,$username,$password,$database
		$dbc = mysql_connect($hostname,$username,$password) ;
		if( !$dbc )
		{
			return NULL ;
		}
		mysql_select_db($database,$dbc) ;
		//$query = mysql_real_escape_string($query,$dbc) ;
		$result = mysql_query($query,$dbc) ;
		$numrows = @mysql_numrows($result) ;
		if( $numrows == 0 ) { return NULL ; }
		$row = mysql_fetch_row($result) ;
		if( !isset($row) ) { return NULL ; }
		return $row[0] ;
	}

	function getdata($query)
	{
		include("dbcredentials.php") ; // Sets $hostname,$username,$password,$database
		$dbc = mysql_connect($hostname,$username,$password) ;
		if( !$dbc )
		{
			debug("Could not connect to database: ".mysql_error()."\n") ;
			print "Could not connect: ".mysql_error()."</br>\n" ;
			return ;
		}
		mysql_select_db($database,$dbc) ;
		//$query = mysql_real_escape_string($query,$dbc) ;
		$result = mysql_query($query,$dbc) ;
		$numrows = @mysql_numrows($result) ;
		while ($numrows-- > 0 )
		{
			$row = mysql_fetch_row($result) ;
			$data[] = $row ;	// Add each row of table data to the two dimensional array data
		}
		mysql_close($dbc) ;
		return $data ;
	}

	function extent()
	{
		debug("Start extent\n") ;
		$query = "SELECT min(datetime), max(datetime), max(lat), min(lat), max(lon), min(lon) FROM Track ;" ;
		$data = getdata($query) ;
		$row = $data[0] ;
		$items = count($row) ;
		debug("Read ".$items." items from database\n") ;
		$start = $row[0] ;
		$stop = $row[1] ;
		$north = $row[2] ;
		$south = $row[3] ;
		$east = $row[4] ;
		$west = $row[5] ;
		if( $givenstart != "" )
		{
			$start = $givenstart ;
		}
		if( $givenstop != "" )
		{
			$stop = $givenstop ;
		}
		debug("Start=".$start." Stop=".$stop." North=".$north." South=".$south." East=".$east." West=".$west."\n") ;
		if( $items == 6 )
		{ 
			$returnstring = "OK\nStart=".$start."\nStop=".$stop."\nNorth=".$north."\nSouth=".$south."\nEast=".$east."\nWest=".$west."\n" ;
			print $returnstring ;
			debug($returnstring) ;
			return TRUE ;
		}
		return FALSE ;
	}

	function tracklist()
	{
		debug("Start tracklist\n") ;
		$query = "SELECT DISTINCT tx.name FROM Track AS t, txlist AS tx where t.txID=tx.ID;" ;
		$data = getdata($query) ;
		$items = count($data) ;
		debug("Read ".$items." items from database\n") ;
		print "OK\n" ;
		debug("Tracklist:\n") ;
		for( $track = 0 ; $track < $items ; $track++ )
		{
			$row = $data[$track] ;
			$trackname = $row[0] ;
			print "$trackname\n" ;
			debug($trackname." ") ;
		}
		debug("\n") ;
		return TRUE ;
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
//END
