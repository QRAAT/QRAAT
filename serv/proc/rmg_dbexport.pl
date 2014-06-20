#!/usr/bin/perl
#
# This script is part of the backup system and is used to export data from the qraat database est table.
# It creates chunks of a limited size, thereby maximizing the chance of success. It is not always possible to
# export data by day or even by hour without exceeding the resources available to mysqld.
#
# This script is given the number of days for which to keep data and it will export all data up to the first
# entry that should remain. Entries are exported ordered by ID value.
#
# rmg_csv --row view=writer user password name </rmg_server/db_auth
#
use strict ;
use warnings ;
use Date::Calc qw( Today Add_Delta_Days ) ;

my $Debug = 0 ;
my $FileName = "dbexport_est.txt" ;

sub usage()
{
	print "Usage: $0 table days size path [DELETE]\n" ;
	print "Exports table entries to file using mysql client.\n" ;
	print "\ttable is the name of the table to export\n" ;
	print "\tdays is the number of days before today that data must remain in the table\n" ;
	print "\tsize is the maximum number of entries in a file before splitting it\n" ;
	print "\tpath is the directory where the files will be written\n" ;
	print "\tDELETE is an optional flag to delete the dumped entries from the table\n" ;
}

sub main()
{
	print localtime()." Starting\n" ;
	my $argc = scalar @ARGV ;
	if( $argc < 4 )
	{
		usage() ;
		return 1 ;
	}
	my $table = $ARGV[0] ;
	my $days = $ARGV[1] ;
	my $max = $ARGV[2] ;
	my $path = $ARGV[3] ;
	my $delete = "" ;
	if( $argc >= 5 )
	{
		$delete = $ARGV[4] ;
	}
	if( (not defined $days) || ($days eq "") )
	{
		print "Missing value for 'days'\n" ;
		return 1 ;
	}
	if( $days <= 0 )
	{
		print "Not a valid value for 'days': $days\n" ;
		return 1 ;
	}
	if( (not defined $max) || ($max eq "") )
	{
		print "Missing value for 'size'\n" ;
		return 1 ;
	}
	if( $max <= 0 )
	{
		print "Not a valid value for 'size': $max\n" ;
		return 1 ;
	}
	if( (not defined $path) || ($path eq "") )
	{
		print "Missing valud for 'path'\n" ;
		return 1 ;
	}
	if( not -d $path )
	{
		print "Path does not exist: '$path'\n" ;
		return 1 ;
	}
	my $delete_qualifier = "will NOT" ;
	if( $delete =~ /DELETE/ )
	{
		print "Cannot currently delete entries, DELETE option ignored.\n" ;
		return 1 ;
		#$delete_qualifier = "WILL" ;
	}
	my @oldest_date = Add_Delta_Days(Date::Calc::Today(),-$days) ;
	my $oldest_datetime = sprintf("%4d-%02d-%02d 00:00:00",@oldest_date) ;
	print "Exporting data from table '$table' older than $days days (before $oldest_datetime).\n" ;
	print "Writing files to '$path' with $max entries each.\n" ;
	print "Entries $delete_qualifier be deleted after writing them to file.\n" ;
	if( $Debug ) { print localtime()." searching for startid\n" ; }
	my $startid = line2(mysqlcommand("select min(id) from est")) ;
	if( (not defined $startid) || ($startid eq "") || ($startid =~ /\D/) || ($startid == 0) )
	{
		print "no valid start\n" ;
		return 1 ;
	}
	if( $Debug ) { print localtime()." searching for finishid\n" ; }
	my $finishid = line2(mysqlcommand("select id from est where datetime >= '$oldest_datetime' order by id asc limit 1")) ;
	if( (not defined $finishid) || ($finishid eq "") || ($finishid == 0) )
	{
		print "no valid finish\n" ;
		return 1 ;
	}
	my $nsteps = int(($finishid - $startid)/$max + 0.5) ;
	if( $nsteps < 1 )
	{
		print "Bad id values: startid=$startid finishid=$finishid\n" ;
		return 1 ;
	}
	print "Start at $startid, finish at $finishid, $nsteps files\n" ;
	while( $startid < $finishid )
	{
		my ( $err, $lastid ) = nextset($startid,$finishid,$max,$path) ;
		if( $err ) 
		{
			print "Bailing out!\n" ;
			return 1 ;
		}
		my $nextid = line2(mysqlcommand("select id from est where id > '$lastid' limit 1")) ;
		if( (not defined $nextid) || ($nextid eq "") || ($nextid == 0) )
		{
			$nextid = $lastid ;
		}
		$startid = $nextid ;
	}
	print localtime()." Finished\n" ;
	return 0 ;
}

sub mysqlcommand($)
{
	my ( $query ) = @_ ;
	if( $Debug ) { print "debug: mysqlcommand: query='$query'\n" ; }
	my $command = "mysql qraat -B -e \"$query\"" ;
	if( $Debug ) { print "debug: command='$command'\n" ; }
	my $result = `$command` ;
	if( $Debug ) { print "debug: result='$result'\n" ; }
	my @array = split /\n/,$result ;
	#print "debug: array=@array\n" ;
	my $refarray = \@array ;
	#print "debug: refarray=$refarray\n" ;
	return $refarray ;
}

sub line2($)
{
	my ( $refarray ) = @_ ;
	my $line = $refarray->[1] ;
	#print "debug: line2: '$line'\n" ;
	return $line ;
}

sub nextset($$$$)
{
	my ( $start, $final_finish, $size, $path ) = @_ ;
	my $finish = $start + $size ;
	if( $finish > $final_finish )
	{
		$finish = $final_finish ;
	}
	if( $Debug ) { print localtime()." counting entries\n" ; }
	my $entries = line2(mysqlcommand("select count(id) from est where id >= '$start' and id < '$finish' order by id asc limit $size")) ;
	if( (not defined $entries) || ($entries eq "") )
	{
		print "Failed to count database entries.\n" ;
		return 1 ;
	}
	if( $Debug ) { print "entries is '$entries'\n" ; }
	if( $Debug ) { print "size=$size\n" ; }
	if( $Debug ) { print localtime()." data select\n" ; }
	my $lines = mysqlcommand("select * from est where id >= '$start' and id < '$finish' order by id asc limit $size") ;
	my $count = scalar @$lines ;
	if( $Debug ) { print "got $count lines\n" ; }
	if( $count < 1 )
	{
		print "Query returned empty result.\n" ;
		return 1 ;
	}
	$count-- ;
	if( $count < $entries )
	{
		print "Query returned incomplete result ($count instead of $entries).\n" ;
		return 1 ;
	}
	my $padstart = sprintf("%.16d",$start) ;
	my $tempfilename = "$path/est_".$padstart."_temporary_filename.txt" ;
	my $fd ;
	if( not defined open($fd,">",$tempfilename) )
	{
		print "Cannot open file '$tempfilename' for writing.\n" ;
		return 1 ;
	}
	if( $Debug ) { print localtime()." file open\n" ; }
	$count = 0 ;
	my $missing = 0 ;
	my $lastid = 0 ;
	my $mindt = "" ;
	for my $line ( @$lines )
	{
		$count++ ;
		my @args = split /\s+/,$line ;
		my $id = $args[0] ;
		if( $id =~ m/(\d)+/ )
		{
			$id = int($id) ;
			if( $lastid == 0 )
			{
				$lastid = $id ;
			}
			my $idstep = $id - $lastid ;
			if( $idstep > 1 )
			{
				$idstep-- ;
				$missing += $idstep ;
				if( $Debug ) { print "step=$idstep, $id-$lastid\n" ; }
			}
			$lastid = $id ;
		}
		my $dt = $args[2]."_".$args[3] ;
		if( $mindt eq "" )
		{
			$mindt = $dt ;
		}
		if( $dt lt $mindt )
		{
			$mindt = $dt ;
		}
		print $fd "$line\n" ;
	}
	close($fd) ;
	if( $Debug ) { print localtime()." file closed\n" ; }
	my $padfinish = sprintf("%.16d",$lastid) ;
	my $filename = "$path/est_".$padstart."_".$padfinish."_".$mindt.".txt" ;
	if( -f $filename )
	{
		print "File '$filename' exists already and must first be manually deleted.\n" ;
		return 1 ;
	}
	if( -f "$filename.gz" )
	{
		print "File '$filename.gz' exists already and must first be manually deleted.\n" ;
		return 1 ;
	}
	if( not rename($tempfilename,$filename) )
	{
		print "Failed to rename '$tempfilename' to '$filename'\n" ;
		return 1 ;
	}
	if( $missing > 0 )
	{
		print "Missing $missing ID values.\n" ;
	}
	if( $Debug )  { print "last id = $lastid\n" ; }
	my $result = `wc -l $filename` ;
	if( ($? != 0) || (not defined $result) or ($result eq "") )
	{
		print "Unable to check file length!\n" ;
		return 1 ;
	}
	my @args = split /\s+/,$result ;
	my $check = $args[0] ;
	if( (defined $check) && ($check ne "") && ($check =~ /\d+/) && ($check > 0) )
	{
		$check = int($check) - 1 ;
	}
	if( $count > 0 )
	{
		$count-- ;
	}
	if( $check != $count )
	{
		print "Bad number of lines (expected $count, found $check) in file '$filename'\n" ;
		return 1 ;
	}
	if( $Debug ) { print localtime()." compressing file $filename\n" ; }
	$result = `gzip -9 $filename` ;
	if( $? != 0 )
	{
		print "Failed to compress the file '$filename'\n" ;
		return 1 ;
	}
	print localtime()." file $filename, $entries entries, $count records, $check lines\n" ;
	return ( 0, $lastid ) ;
}

exit main() ;

#END
