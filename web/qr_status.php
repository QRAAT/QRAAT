<?php
	error_reporting(E_ALL) ;
	date_default_timezone_set("UTC") ;
	include("qr_variables.php") ;	// sets system path and configuration variables

	function read_csv($filename)
	{
		$data = array() ;
		if( file_exists($filename) )
		{
			$timestamp = filemtime($filename) ;
			$datetime = date("Y M d l H:i:s T",$timestamp) ;
			$metadata = array( $filename, $datetime ) ;
			$data[] = $metadata ;
			$fh=fopen($filename,"r") ;
			if( $fh )
			{
				while( $line = fgets($fh) )
				{
					$argv = explode(",",$line) ;
					$argc = count($argv) ;
					if( $argc > 1 )
					{
						$data[] = $argv ;
					}
				}
				fclose($fh) ;
			}
		}
		return $data ;
	}

	function show_data($data,$title)
	{
		print "<h2>$title</h2>\n" ;
		if( count($data) )
		{
			$metadata = array_shift($data) ;
			$filename = $metadata[0] ;
			$filemtime = $metadata[1] ;
			print "<p>$filename last modified $filemtime</p>\n" ;
			if( count($data) )
			{
				print "<table class=\"status\">" ;
				$header = array_shift($data) ;
				print "<tr>" ;
				foreach( $header as $cell )
				{
					print "<th>" ;
					print htmlspecialchars($cell) ;
					print "</th>" ;
				}
				print "</tr>" ;
				foreach( $data as $row )
				{
					print "<tr>" ;
					foreach( $row as $cell )
					{
						print "<td>" ;
						print htmlspecialchars($cell) ;
						print "</td>" ;
					}
					print "</tr>" ;
				}
				print "</table>" ;
			}
		}
		else
		{
			print "<p>No data</p>\n" ;
		}
	}

	function fixup_timestamp(&$data)
	{
		foreach( $data as &$row )
		{
			$timestamp = intval($row[0]) ;
			if( $timestamp > 0 )
			{
				$datetime = date("Y M d l H:i:s T",$timestamp) ;
				$row[0] = $datetime ;
			}
		}
	}

	function qr_status()
	{
		global $path_to_tx_csv ;
		global $path_to_sitelist_csv ;
		global $path_to_status_log ;
		print "<p>Date is: ".date(DATE_RFC822)."</p>" ;
		print "<p>System status is: GOOD!</p>" ;
		$data = read_csv($path_to_sitelist_csv) ;
		show_data($data,"Site configuration file") ;
		$data = read_csv($path_to_tx_csv) ;
		show_data($data,"Transmitter configuration file") ;
		$data = read_csv($path_to_status_log) ;
		fixup_timestamp($data) ;
		show_data($data,"Status log file") ;
	}
?>
