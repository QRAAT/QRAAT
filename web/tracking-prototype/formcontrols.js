//
//	Bodega Marine Laboratory
//	Helper code for form controls
//	Marcel Losekoot
//	Updated 2011-02-02

// Globals
var FIRSTYEAR=2000 ;

function initformcontrols()	// Initializes the form date controls and sets them to current dates
{
	var html ;	// holds the html string for the control option list
	//
	// Get current datetime and use it to set default selections
	var now = new Date() ;			// get the current date and time exactly once
	var start = new Date(now.getTime()) ;	// copy the current date to the start date, ...
	start.setDate(start.getDate()-1) ;	// ... then back it up one day
	var stop = new Date(now.getTime()) ;	// copy the current date to the stop date
	var startyear = start.getUTCFullYear() ;
	var startmonth = start.getUTCMonth() ;	// starts at 0
	var startday = start.getUTCDate() ;	// starts at 1
	var starthour = start.getUTCHours() ;
	var startmin = start.getUTCMinutes() ;
	var startsec = start.getUTCSeconds() ;
	var startstring = startyear+"/"+startmonth+"/"+startday+" "+starthour+":"+startmin+":"+startsec ;// check individual variables
	var stopyear = stop.getUTCFullYear() ;
	var stopmonth = stop.getUTCMonth() ;	// starts at 0
	var stopday = stop.getUTCDate() ;	// starts at 1
	var stophour = stop.getUTCHours() ;
	var stopmin = stop.getUTCMinutes() ;
	var stopsec = stop.getUTCSeconds() ;
	var stopstring = stopyear+"/"+stopmonth+"/"+stopday+" "+stophour+":"+stopmin+":"+stopsec ;// check individual variables
	document.getElementById('debug_text').value = 'setformcontrols: start='+startstring+':00, stop='+stopstring+':00' ;
	var tzoffset = now.getTimezoneOffset() ;
	tzoffset /= 60 ;
	tzoffset *= 10 ;
	tzoffset = parseInt(tzoffset) ;
	tzoffset /= 10 ;
	var offsetstring ;
	if( tzoffset > 0 )
	{
		offsetstring = tzoffset+" hours behind UTC." ;
	}
	if( tzoffset < 0 )
	{
		offsetstring = tzoffset+" hours ahead of UTC." ;
	}
	if( tzoffset < 0 )
	{
		offsetstring = " the same as UTC." ;
	}
	var nowyear = now.getFullYear() ;
	var nowmonth = now.getMonth() ;	// starts at 0
	var monthnames = [ 'January','February','March','April','June','July','August','September','October','November','December'] ;
	var nowmonthname = monthnames[nowmonth] ;
	var nowday = now.getDate() ;		// starts at 1
	var nowhour = now.getHours() ;
	if( nowhour < 10 ) nowhour = "0"+nowhour ;
	var nowminute = now.getMinutes() ;
	if( nowminute < 10 ) nowminute = "0"+nowminute ;
	var nowstring = nowhour+":"+nowminute+" on "+nowmonthname+" "+nowday+", "+nowyear ;
	document.getElementById('timezonetext').innerHTML = "Your local time is "+nowstring+" and is "+offsetstring ;
	//
	builddatecontrols(FIRSTYEAR,stopyear)	// Build form date controls, years start at FIRSTYEAR, stopyear is set to this year
	buildtrackcontrols([]) ;		// Set form track control from an empty array
	setdates(startyear,startmonth,startday,starthour,0,0,stopyear,stopmonth,stopday,stophour,0,0)
	doChangeOptions() ; // called on startup to copy the default settings to the selectedoptions control
}

function builddatecontrols(startyear,stopyear)	// Build the form date controls
{
	var control ;
	var index ;
	//
	// Build option list for year controls
	control = document.getElementById('controlform_startyear') ;
	for( var year = startyear ; year <= stopyear ; year++ )
	{
		index = year-startyear ;
		control.options[index] = new Option(year,year,false,false) ;
	}
	control = document.getElementById('controlform_stopyear') ;
	for( var year = startyear ; year <= stopyear ; year++ )
	{
		index = year-startyear ;
		control.options[index] = new Option(year,year,false,false) ;
	}
	//
	// Build option list for month controls
	control = document.getElementById('controlform_startmonth') ;
	for( var month = 1 ; month <= 12 ; month++ )
	{
		index = month-1 ;
		var pad = "" ;
		if( month < 10 ) pad = "0" ;
		pad += month ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	control = document.getElementById('controlform_stopmonth') ;
	for( var month = 1 ; month <= 12 ; month++ )
	{
		index = month-1 ;
		var pad = "" ;
		if( month < 10 ) pad = "0" ;
		pad += month ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	//
	// Build option list for day controls
	control = document.getElementById('controlform_startday') ;
	for( var day = 1 ; day <= 31 ; day++ )
	{
		index = day-1 ;
		var pad = "" ;
		if( day < 10 ) pad = "0" ;
		pad += day ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	control = document.getElementById('controlform_stopday') ;
	for( var day = 1 ; day <= 31 ; day++ )
	{
		index = day-1 ;
		var pad = "" ;
		if( day < 10 ) pad = "0" ;
		pad += day ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	//
	// Build option list for hour controls
	control = document.getElementById('controlform_starthour') ;
	for( var hour = 0 ; hour <= 23 ; hour++ )
	{
		index = hour ;
		var pad = "" ;
		if( hour < 10 ) pad = "0" ;
		pad += hour ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	control = document.getElementById('controlform_stophour') ;
	for( var hour = 0 ; hour <= 23 ; hour++ )
	{
		index = hour ;
		var pad = "" ;
		if( hour < 10 ) pad = "0" ;
		pad += hour ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	//
	// Build option list for min controls
	control = document.getElementById('controlform_startmin') ;
	for( var min = 0 ; min <= 59 ; min++ )
	{
		index = min ;
		var pad = "" ;
		if( min < 10 ) pad = "0" ;
		pad += min ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	control = document.getElementById('controlform_stopmin') ;
	for( var min = 0 ; min <= 59 ; min++ )
	{
		index = min ;
		var pad = "" ;
		if( min < 10 ) pad = "0" ;
		pad += min ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	//
	// Build option list for sec controls
	control = document.getElementById('controlform_startsec') ;
	for( var sec = 0 ; sec <= 59 ; sec++ )
	{
		index = sec ;
		var pad = "" ;
		if( sec < 10 ) pad = "0" ;
		pad += sec ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
	control = document.getElementById('controlform_stopsec') ;
	for( var sec = 0 ; sec <= 59 ; sec++ )
	{
		index = sec ;
		var pad = "" ;
		if( sec < 10 ) pad = "0" ;
		pad += sec ;
		control.options[index] = new Option(pad,pad,false,false) ;
	}
}

function buildtrackcontrols(tracknames)
{
	var control ;
	var index ;
	//
	// Build option list for track control
	control = document.getElementById('controlform_track') ;
	control.options[0] = new Option("All Tracks","All",false,false) ;	// Start the list with "All Tracks"
	control.selectedIndex = 0 ;	// select "All"
	ntracks = tracknames.length ;
	for( var track = 1 ; track <= ntracks ; track++ )	// NB: tracknames starts at 1!
	{
		index = track ;
		trackname = tracknames[track] ;
		if( trackname != undefined )
		{
			if( trackname != "" )
			{
				control.options[index] = new Option(trackname,trackname,false,false) ;
			}
		}
	}
	changetrack() ;
}

function resetDates(extent)		// sets the start and finish date controls according to the values in global Extent
{
	if( extent == undefined )
	{
		return ;
	}
	if( extent.length < 3 )
	{
		return ;
	}
	var start = extent[1] ;	// YYYY-MM-DD HH:MM:SS
	if( start == undefined )
	{
		return ;
	}
	var startyear = start.substring(0,4) ;
	var startmonth = start.substring(5,7) ;
	var startday = start.substring(8,10) ;
	var starthour = start.substring(11,13) ;
	var startmin = start.substring(14,16) ;
	var startsec = start.substring(17,19) ;
	var stop = extent[2] ;
	if( stop == undefined )
	{
		return ;
	}
	var stopyear = stop.substring(0,4) ;
	var stopmonth = stop.substring(5,7) ;
	var stopday = stop.substring(8,10) ;
	var stophour = stop.substring(11,13) ;
	var stopmin = stop.substring(14,16) ;
	var stopsec = stop.substring(17,19) ;
	setdates(startyear,startmonth,startday,starthour,startmin,startsec,stopyear,stopmonth,stopday,stophour,stopmin,stopsec)	// set form date controls
}

function setdates(startyear,startmonth,startday,starthour,startmin,startsec,stopyear,stopmonth,stopday,stophour,stopmin,stopsec) // set form date controls
{
	var control ;
	var index ;
	//
	control = document.getElementById('controlform_startyear') ;
	control.selectedIndex = startyear-FIRSTYEAR ;	// select the start year
	changestartyear() ;
	control = document.getElementById('controlform_stopyear') ;
	control.selectedIndex = stopyear-FIRSTYEAR ;	// select the stop year
	changestopyear() ;
	control = document.getElementById('controlform_startmonth') ;
	control.selectedIndex = startmonth-1 ;	// select the start month
	changestartmonth() ;
	control = document.getElementById('controlform_stopmonth') ;
	control.selectedIndex = stopmonth-1 ;	// select the stop month
	changestopmonth() ;
	control = document.getElementById('controlform_startday') ;
	control.selectedIndex = startday-1 ;	// select the start day
	changestartday() ;
	control = document.getElementById('controlform_stopday') ;
	control.selectedIndex = stopday-1 ;	// select the stop day
	changestopday() ;
	control = document.getElementById('controlform_starthour') ;
	control.selectedIndex = starthour ;	// select the start hour
	changestarthour() ;
	control = document.getElementById('controlform_stophour') ;
	control.selectedIndex = stophour ;	// select the stop hour
	changestophour() ;
	control = document.getElementById('controlform_startmin') ;
	control.selectedIndex = startmin ;	// select the start min
	changestartmin() ;
	control = document.getElementById('controlform_stopmin') ;
	control.selectedIndex = stopmin ;	// select the stop min
	changestopmin() ;
	control = document.getElementById('controlform_startsec') ;
	control.selectedIndex = startsec ;	// select the start sec
	changestartsec() ;
	control = document.getElementById('controlform_stopsec') ;
	control.selectedIndex = stopsec ;	// select the stop sec
	changestopsec() ;
	//
}

function changestartyear()
{
	var object = document.getElementById('controlform_startyear') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstartyear').value = value ;	// copy the value to control selectedstartyear
			document.getElementById('debug_text').value = 'changestartyear: selectedstartyear='+value ;
		}
	}
	updatelocalstart() ;
}

function changestartmonth()
{
	var object = document.getElementById('controlform_startmonth') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstartmonth').value = value ;	// copy the value to control selectedstartmonth
			document.getElementById('debug_text').value = 'changestartmonth: selectedstartmonth='+value ;
		}
	}
	updatelocalstart() ;
}

function changestartday()
{
	var object = document.getElementById('controlform_startday') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstartday').value = value ;	// copy the value to control selectedstartday
			document.getElementById('debug_text').value = 'changestartday: selectedstartday='+value ;
		}
	}
	updatelocalstart() ;
}

function changestarthour()
{
	var object = document.getElementById('controlform_starthour') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstarthour').value = value ;	// copy the value to control selectedstarthour
			document.getElementById('debug_text').value = 'changestarthour: selectedstarthour='+value ;
		}
	}
	updatelocalstart() ;
}

function changestartmin()
{
	var object = document.getElementById('controlform_startmin') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstartmin').value = value ;	// copy the value to control selectedstartmin
			document.getElementById('debug_text').value = 'changestartmin: selectedstartmin='+value ;
		}
	}
	updatelocalstart() ;
}

function changestartsec()
{
	var object = document.getElementById('controlform_startsec') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstartsec').value = value ;	// copy the value to control selectedstartsec
			document.getElementById('debug_text').value = 'changestartsec: selectedstartsec='+value ;
		}
	}
	updatelocalstart() ;
}

function changestopyear()
{
	var object = document.getElementById('controlform_stopyear') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstopyear').value = value ;	// copy the value to control selectedstopyear
			document.getElementById('debug_text').value = 'changestopyear: selectedstopyear='+value ;
		}
	}
	updatelocalstop() ;
}

function changestopmonth()
{
	var object = document.getElementById('controlform_stopmonth') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstopmonth').value = value ;	// copy the value to control selectedstopmonth
			document.getElementById('debug_text').value = 'changestopmonth: selectedstopmonth='+value ;
		}
	}
	updatelocalstop() ;
}

function changestopday()
{
	var object = document.getElementById('controlform_stopday') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstopday').value = value ;	// copy the value to control selectedstopday
			document.getElementById('debug_text').value = 'changestopday: selectedstopday='+value ;
		}
	}
	updatelocalstop() ;
}

function changestophour()
{
	var object = document.getElementById('controlform_stophour') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstophour').value = value ;	// copy the value to control selectedstophour
			document.getElementById('debug_text').value = 'changestophour: selectedstophour='+value ;
		}
	}
	updatelocalstop() ;
}

function changestopmin()
{
	var object = document.getElementById('controlform_stopmin') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstopmin').value = value ;	// copy the value to control selectedstopmin
			document.getElementById('debug_text').value = 'changestopmin: selectedstopmin='+value ;
		}
	}
	updatelocalstop() ;
}

function changestopsec()
{
	var object = document.getElementById('controlform_stopsec') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedstopsec').value = value ;	// copy the value to control selectedstopsec
			document.getElementById('debug_text').value = 'changestopsec: selectedstopsec='+value ;
		}
	}
	updatelocalstop() ;
}

function updatelocalstart()
// sets the form control controlform_localstart to a string representing the local version of the UTC start date and time
{
	var startyear = document.getElementById('controlform_selectedstartyear').value ;
	if( ! startyear ) { return ; }
	var startmonth = document.getElementById('controlform_selectedstartmonth').value ;
	if( ! startmonth ) { return ; }
	var startday = document.getElementById('controlform_selectedstartday').value ;
	if( ! startday ) { return ; }
	var starthour = document.getElementById('controlform_selectedstarthour').value ;
	if( ! starthour ) { return ; }
	var startmin = document.getElementById('controlform_selectedstartmin').value ;
	if( ! startmin ) { return ; }
	var startsec = document.getElementById('controlform_selectedstartsec').value ;
	if( ! startsec ) { return ; }
	var startdate = new Date() ;
	startdate.setUTCFullYear(startyear) ;
	startdate.setUTCMonth(startmonth-1) ;
	startdate.setUTCDate(startday) ;
	startdate.setUTCHours(starthour) ;
	startdate.setUTCMinutes(startmin) ;
	startdate.setUTCSeconds(startsec) ;
	var localyear = startdate.getFullYear() ;
	var localmonth = startdate.getMonth()+1 ;
	var localday = startdate.getDate() ;
	if( localday < 10 )
	{
		localday = "0"+localday ;
	}
	var localhour = startdate.getHours() ;
	if( localhour < 10 )
	{
		localhour = "0"+localhour ;
	}
	var localmin = startdate.getMinutes() ;
	if( localmin < 10 )
	{
		localmin = "0"+localmin ;
	}
	var localsec = startdate.getSeconds() ;
	if( localsec < 10 )
	{
		localsec = "0"+localsec ;
	}
	var localstring = localyear+"/"+localmonth+"/"+localday+" "+localhour+":"+localmin+":"+localsec+" local" ; // locale string ???
	document.getElementById('controlform_localstart').value = localstring ;
}

function updatelocalstop()
// sets the form control controlform_localstop to a string representing the local version of the UTC stop date and time
{
	var stopyear = document.getElementById('controlform_selectedstopyear').value ;
	if( ! stopyear ) { return ; }
	var stopmonth = document.getElementById('controlform_selectedstopmonth').value ;
	if( ! stopmonth ) { return ; }
	var stopday = document.getElementById('controlform_selectedstopday').value ;
	if( ! stopday ) { return ; }
	var stophour = document.getElementById('controlform_selectedstophour').value ;
	if( ! stophour ) { return ; }
	var stopmin = document.getElementById('controlform_selectedstopmin').value ;
	if( ! stopmin ) { return ; }
	var stopsec = document.getElementById('controlform_selectedstopsec').value ;
	if( ! stopsec ) { return ; }
	var stopdate = new Date() ;
	stopdate.setUTCFullYear(stopyear) ;
	stopdate.setUTCMonth(stopmonth-1) ;
	stopdate.setUTCDate(stopday) ;
	stopdate.setUTCHours(stophour) ;
	stopdate.setUTCMinutes(stopmin) ;
	stopdate.setUTCSeconds(stopsec) ;
	var localyear = stopdate.getFullYear() ;
	var localmonth = stopdate.getMonth()+1 ;
	var localday = stopdate.getDate() ;
	if( localday < 10 )
	{
		localday = "0"+localday ;
	}
	var localhour = stopdate.getHours() ;
	if( localhour < 10 )
	{
		localhour = "0"+localhour ;
	}
	var localmin = stopdate.getMinutes() ;
	if( localmin < 10 )
	{
		localmin = "0"+localmin ;
	}
	var localsec = stopdate.getSeconds() ;
	if( localsec < 10 )
	{
		localsec = "0"+localsec ;
	}
	var localstring = localyear+"/"+localmonth+"/"+localday+" "+localhour+":"+localmin+":"+localsec+" local" ; // locale string ???
	document.getElementById('controlform_localstop').value = localstring ;
}

function changetrack()
{
	var object = document.getElementById('controlform_track') ;
	if( object )
	{
		var index = object.selectedIndex ;
		if( index >= 0 )
		{
			var value = object.options[index].value ;
			document.getElementById('controlform_selectedtrack').value = value ;	// copy the value to control selectedstopsec
			document.getElementById('debug_text').value = 'changetrack: selectedtrack='+value ;
		}
	}
}

function doChangeOptions()
// This function gets called each time any of the option controls get touched.
// Calls redrawkml() to refresh the KML overlay
{
	// selectedoptions = showtrace+coloreach+markstart+markend+showstuck ;
	var showtrace = "X" ;
	var coloreach = "X" ;
	var markstart = "X" ;
	var markend = "X" ;
	var showstuck = "X" ;
	var selectedoptions = "" ;
	var control ;
	// In the code below, assume all option radio controls are of length 2, with position 0 meaning 'yes' and position 1 meaning 'no'
	control = document.getElementsByName("showtrace") ;
	if( control )
	{
		if( control[0].checked )
		{
			showtrace = "Y" ;
		}
		if( control[1].checked )
		{
			showtrace = "N" ;
		}
	}
	control = document.getElementsByName("coloreach") ;
	if( control )
	{
		if( control[0].checked )
		{
			coloreach = "Y" ;
		}
		if( control[1].checked )
		{
			coloreach = "N" ;
		}
	}
	control = document.getElementsByName("markstart") ;
	if( control )
	{
		if( control[0].checked )
		{
			markstart = "Y" ;
		}
		if( control[1].checked )
		{
			markstart = "N" ;
		}
	}
	control = document.getElementsByName("markend") ;
	if( control )
	{
		if( control[0].checked )
		{
			markend = "Y" ;
		}
		if( control[1].checked )
		{
			markend = "N" ;
		}
	}
	selectedoptions = showtrace+coloreach+markstart+markend ;
	document.getElementById('controlform_selectedoptions').value = selectedoptions ;
	document.getElementById('debug_text').value = 'doChangeOptions: selectedoptions='+selectedoptions ;
	//redrawkml() ;	// calls a function in the main code to refresh the KML overlay
}

//END
