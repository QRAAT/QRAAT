<html>
<head>
<style type="text/css">
table.status {
	font-family: verdana,arial,sans-serif;
	font-size:11px;
	color:#333333;
	border-width: 1px;
	border-color: #666666;
	border-collapse: collapse;
}
table.status th {
	border-width: 1px;
	padding: 8px;
	border-style: solid;
	border-color: #666666;
	background-color: #dedede;
}
table.status td {
	border-width: 1px;
	padding: 8px;
	border-style: solid;
	border-color: #666666;
	background-color: #ffffff;
}
</style>
</head>
<body>
<?php
	print "<p><a href='status.phtml'>Back</a></p>\n" ;
	include($_SERVER['DOCUMENT_ROOT']."/dbcredentials.php") ;
	$data = getdata("select count(id),min(datetime),max(datetime) from fest where datetime > date_add(now(), interval -1 day)") ;
	$count = $data[0][0] ;
	$dtstart = $data[0][1] ;
	$dtstop = $data[0][2] ;
	if( $count > 0 )
	{
		print "Showing {$data[0][0]} entries between {$data[0][1]} and {$data[0][2]} UTC<br />\n" ;
		$data = getdata("select frequency,datetime,name,fdsp,fdsnr,band3,band10 from fest,sitelist where sitelist.id = fest.site and datetime > date_add(now(), interval -1 day) order by frequency,datetime,name") ;
		showdata(array("Frequency","Datetime (UTC)","Site","Power","SNR","Band3dB","Band10dB"),$data) ;
	}
	else
	{
		print "No data.\n" ;
	}
	print "</body>\n</html>\n" ;

	function getdata($query)
	{
		include("dbcredentials.php") ; // Sets $hostname,$username,$password,$database
		$dbc = @mysql_connect($hostname,$username,$password) ;
		if( !$dbc )
		{
			print "Could not connect: ".mysql_error()."</br>\n" ;
			return ;
		}
		mysql_select_db($database,$dbc) ;
		$query = mysql_real_escape_string($query,$dbc) ;
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

	function showdata($headings,$data)
	{
		$numrows = count($data) ;
		if( $numrows > 0 )
		{
			print "<table class='status'>\n" ;
			print "<tr>\n" ;
			foreach( $headings as $heading )
			{
				print "<th>$heading</th>\n" ;
			}
			print "</tr>\n" ;
			foreach( $data as $row )
			{
				print "<tr>\n" ;
				$numvalues = count($row) ;
				if( $numvalues > 1 )
				{
					foreach( $row as $value )
					{
						print "<td>$value</td>\n" ;
					}
				}
				else
				{
					print "<td>$row</td>\n" ;
				}
				print "</tr>\n" ;
			}
			print "</table>\n" ;
		}
		else
		{
			print "No rows</br>\n" ;
		}
	}
?>
</body>
</html>
