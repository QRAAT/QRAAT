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
<p><a href='status.phtml'>Back</a></p>
<?php
	$input_duration_1hour = "unchecked" ;
	$input_duration_2hours = "unchecked" ;
	$input_duration_6hours = "unchecked" ;
	$input_duration_1day = "unchecked" ;
	$input_duration_2days = "unchecked" ;
	$interval = 6*3600 ;
#	if( isset($_POST['radio_duration']) )
#	{
#		print "<p>debug: POST['radio_duration']=".$_POST['radio_duration']."</p>\n" ;
#	}
	if( isset($_POST['radio_duration']) )
	{
		$radio_duration = $_POST['radio_duration'] ;
		#print "<p>debug: radio_duration='$radio_duration'</p>\n" ;
		if( $radio_duration == "1hour" )
		{
			$input_duration_1hour = "checked" ;
			$interval = 3600 ;
		}
		if( $radio_duration == "2hours" )
		{
			$input_duration_2hours = "checked" ;
			$interval = 2*3600 ;
		}
		if( $radio_duration == "6hours" )
		{
			$input_duration_6hours = "checked" ;
			$interval = 6*3600 ;
		}
		if( $radio_duration == "1day" )
		{
			$input_duration_1day = "checked" ;
			$interval = 24*3600 ;
		}
		if( $radio_duration == "2days" )
		{
			$input_duration_2days = "checked" ;
			$interval = 48*3600 ;
		}
	}
	else
	{
		$input_duration_6hours = "checked" ;
		$interval = 6*3600 ;
	}
?>
<form name="form_showfest" method="post" action="showfest.php">
	<input type="radio" name="radio_duration" value="1hour" onclick="this.form.submit();" <?php print $input_duration_1hour; ?>>1 Hour
	<input type="radio" name="radio_duration" value="2hours" onclick="this.form.submit();" <?php print $input_duration_2hours; ?>>2 Hours
	<input type="radio" name="radio_duration" value="6hours" onclick="this.form.submit();" <?php print $input_duration_6hours; ?>>6 Hours
	<input type="radio" name="radio_duration" value="1day" onclick="this.form.submit();" <?php print $input_duration_1day; ?>>1 Day
	<input type="radio" name="radio_duration" value="2days" onclick="this.form.submit();" <?php print $input_duration_2days; ?>>2 Days
</form>
<?php
	include($_SERVER['DOCUMENT_ROOT']."/dbcredentials.php") ;
	if( $interval < 1 )
	{
		$interval = 6*3600 ; # 6hours
	}
	$query = "select count(id),min(datetime),max(datetime) from fest where datetime > date_add(utc_timestamp(),interval -$interval second)" ;
	$data = getdata($query) ;
	$count = $data[0][0] ;
	$dtstart = $data[0][1] ;
	$dtstop = $data[0][2] ;
	if( $count > 0 )
	{
		print "Showing {$data[0][0]} entries between {$data[0][1]} and {$data[0][2]} UTC<br />\n" ;
		$data = getdata("select frequency,datetime,name,fdsp,fdsnr,band3,band10 from fest,site where site.ID = fest.siteid and datetime > date_add(utc_timestamp(), interval -$interval second) order by frequency,datetime,name") ;
		showdata(array("Frequency","Datetime (UTC)","Site","Power","SNR","Band3dB","Band10dB"),$data) ;
	}
	else
	{
		print "No data.\n" ;
	}

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
