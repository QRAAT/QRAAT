//
//	Marcel Losekoot
//	Updated 2012-05-07
//

// Program globals
var map = null ;				// Google Maps object for the map
var debug = null ;
var Extent = new Array() ;			// A list of coordinates that define the map extent
var TrackList = new Array() ;			// A list of track names to select from
var PROGRESSTIMEOUT = 60*1000 ;			// The maximum time we give the server to respond, in milliseconds
var progresstimer = null ;			// A handle for the progress timer
var request = null ;				// handle for AJAX request
var requesting = false ;			// flag set when an AJAX request is in progress
var KmlFilename = null ;			// the filename for the current kml file, resulting from a doMakeKML()
var KmlUrl = null ;				// the URL for the kml file
var geoXmlKml = null ;				// object for the KML overlay
var KMLURLROOT = "localhost/tracks/tmp/" ;	// The root part of the URL at which the drifter trajectory KML file is stored

var DebugSelectedTrack = "" ;

function load()
{
	debug = document.getElementById('debug_text') ;
	debug.value = "load: started" ;
	if (GBrowserIsCompatible())
	{
		map = new GMap2(document.getElementById("map"),{draggableCursor:'default'});	// initialize the map div, change cursor to pointer
		//document.getElementById("map").style.backgroundImage = "url(loading.jpg)";	// load the 'loading, please wait' message
		var mapCenter = new GLatLng(0,0) ;
		map.setCenter(mapCenter, 2);					// this sets the map to the previously defined coordinates and zoom
		map.setMapType(G_HYBRID_MAP);					// this sets the map type to be Hybrid (Map+Satellite)
		map.addControl(new GSmallZoomControl());			// this adds the +|- zoom control buttons
		map.addControl(new GScaleControl());				// this adds the scale bar to the map
		map.addControl(new GMapTypeControl());				// this adds the 'Map|Satellite|Hybrid' map control buttons
		click = GEvent.addListener(map, "click", clickHandler);		// this causes clickHandler to be called when the mouse clicks on the map
		GEvent.addListener(map, "mousemove", moveHandler);		// this causes moveHandler to be called when the mouse moves over the map
		//
		// ====== Restricting the range of Zoom Levels =====
		// Get the list of map types      
		//var mt = map.getMapTypes();
		// Overwrite the getMinimumResolution() and getMaximumResolution() methods
		//for (var i=0; i<mt.length; i++)
		//{
		//	mt[i].getMinimumResolution = function() {return 2;}
		//	mt[i].getMaximumResolution = function() {return 20;}
		//}
		//
		getextent() ;		// Get extent data from server, sets map view extent
		initformcontrols() ;	// init form controls, specifically the start and end dates
	}
	else
	{
		debug.value = "load: GBrowserIsCompatible() returned false" ;
		alert("Sorry, the Google Maps API is not compatible with this browser");
	}
}

function clickHandler(overlay, latlng)
{
	debug.value = "clickHandler: called" ;
	if( latlng == null )
		return ;	// Click was intended for a GM object, ignore it.
	if( (current_latlng != null) && current_latlng.equals(latlng) )
		return;  //click event twice
	current_latlng = latlng.copy() ;

	if (latlng) 
	{
		//doAddMarker(latlng) ;
	}
}

function moveHandler(latlng)
{
	document.getElementById("lat").value = mytruncate(latlng.lat());
	document.getElementById("lon").value = mytruncate(latlng.lng());
}

function doAddMarker(latlng)
{
	var slat = '';
	var slng = '';
	slat = mytruncate(latlng.lat())-0;
	slng = mytruncate(latlng.lng())-0;
	//alert('debug: click at ' + slat + ';' + slng);
	debug.value = "doAdd: added a marker at "+slng+","+slat ;
	if( marker != null )
	{
		map.removeOverlay(marker) ;	// zap marker at old position, destroy old marker
	}
	marker = new GMarker(latlng) ;	// create new marker, the old one is gone
	map.addOverlay(marker);	  		// show the new marker as an overlay on the map
}

function mytruncate(val)
{
	var v = '' + val;
	var ind = v.indexOf(".");
	if (ind != -1)
	{
		return v.substring(0, ind+7);	// to show 6 decimal places
	}
	else
	{
		return v + ".000000";
	}
}

function createProgress(messagestring)		// Display progress text in a special div
{
	document.getElementById('message').value = messagestring ;
}

function OLDcreateProgress(messagestring)	// Create and display the progress window
{
		// create a new document div for the page overlay and append it to the page
		var overlay = document.createElement("div");
		overlay.setAttribute("id","overlay");
		overlay.setAttribute("class","overlay");
		document.body.appendChild(overlay);
		var overlay = document.createElement("div");
		overlay.setAttribute("id","overlaydialog");
		overlay.setAttribute("class","overlaydialog");
		overlay.setAttribute("tabindex","-1");
		overlay.setAttribute("role","dialog");
		// create a new document div for the dialog box contents and append it to the page
		var tablestyle = "align=\"center\"" ;
		var tablerow1 = "<tr><td align=\"center\"><img src=\"ajax-loader.gif\" width=\"16\" height=\"16\" alt=\"\" ></td></tr>" ;
		var tablerow2 = "<tr><td align=\"center\">"+messagestring+"</td></tr>" ;
		var tablerow3 = "<tr><td align=\"center\"><input type=\"button\" id=\"stop\" name=\"stop\" value=\"Stop\" onclick=\"doStopQuery();\"></td></tr>" ;
		var table = "<table "+tablestyle+tablerow1+tablerow2+tablerow3+"</table>" ;
		var html = "<div>"+table+"</div" ;
		overlay.innerHTML = html ;
		document.body.appendChild(overlay);
}

function doStopQuery()
{
	if( confirm("Stop the query?") )
	{
		clearTimeout(progresstimer) ;
		removeProgress() ;
		if( requesting )
		{
			request.onreadystatechange = function () {}
			request.abort() ;
			requesting = false ;
		}
        }
}

function removeProgress()	// Removes the progress text
{
	document.getElementById('message').value = "" ;
}

function OLDremoveProgress()	// Removes the progress window
{
	var overlay = document.getElementById("overlay") ;
	var overlaydialog = document.getElementById("overlaydialog") ;
	if( (overlay == null) || (overlaydialog == null) )
	{
		debug.value = 'removeProgress: cannot remove overlay. This should never happen :(' ;
	}
	else
	{
		// remove the overlay and overlay dialog divs from the document
		document.body.removeChild(document.getElementById("overlay"));
		document.body.removeChild(document.getElementById("overlaydialog"));
	}
}

function timeoutProgress()	// cleans up the progress window and server communications when the progress timeout goes off
{
	if( requesting )	// cancel the http request
	{
		request.onreadystatechange = function () {}
		request.abort() ;
		requesting = false ;
	}
	clearTimeout(progresstimer) ;
	removeProgress() ;	// remove the progress window
	alert('The server does not seem to be responding, please try again later.\nIf this problem persists, please contact us.') ;
}

function doDownloadKML()	// Downloads the KML file from the server to the browser
{
	if( KmlUrl != null )
	{
		var iframe_downloadkml = document.getElementById("iframe_downloadkml") ;
		if( iframe_downloadkml )
		{
			iframe_downloadkml.src = KmlUrl ;
		}
	}
}

function doExport()		// Shows the URL for the KML file with the RMG data
{
	if( KmlUrl != null )
	{
		var message = "Export these results to a separate Google Map" ;
		if( prompt(message,KmlUrl) )
		{
			var url = "http://maps.google.com/maps?q="+encodeURI(KmlUrl) ;
			window.open(url,"RMG Data") ;
		}
	}
}

function showExtent()
{
	//var start = Extent['Start'] ;
	var start = Extent[1] ;
	//var finish = Extent['Stop'] ;
	var stop = Extent[2] ;
	//var north = Extent['North'] ;
	var north = Extent[3] ;
	//var south = Extent['South'] ;
	var south = Extent[4] ;
	//var east = Extent['East'] ;
	var east = Extent[5] ;
	//var west = Extent['West'] ;
	var west = Extent[6] ;
	var result = 'Start:'+start+' Stop:'+stop+' North:'+north+' South:'+south+' East:'+east+' West:'+west+'\n' ;
	alert(result) ;
}

function showTrackList()
{
	var ntrack = TrackList.length ;
	var trackstring = ntrack+" tracks: " ;
	for( var track = 0 ; track < ntrack ; track++ )
	{
		trackstring += TrackList[track]+" " ;
	}
	alert(trackstring) ;
}

function recenterMap(extent)		// Recenters the map using the given extent
{
	var north = Number(extent[3]) ;
	var south = Number(extent[4]) ;
	var east = Number(extent[5]) ;
	var west = Number(extent[6]) ;
	if( (north != 0) && (south != 0) && (east != 0) && (west != 0) )
	{
		var lat = (north+south)/2 ;
		var lng = (east+west)/2 ;
		var ne = new GLatLng(north,east) ;
		var sw = new GLatLng(south,west) ;
		var bounds = new GLatLngBounds() ;
		bounds.extend(ne) ;
		bounds.extend(sw) ;
		var zoomLevel = map.getBoundsZoomLevel(bounds) ;
		//zoomLevel++ ;
		debug.value = "debug: lat="+lat+" lng="+lng+" n="+north+" s="+south+" e="+east+" w="+west+" z="+zoomLevel ;
		//if( zoomLevel > 12 ) { zoomLevel = 12 ; }
		if( zoomLevel < 1 ) { zoomLevel = 1 ; }
		map.setZoom(zoomLevel) ;
		var latlng = new GLatLng(lat,lng) ;
		map.setCenter(latlng) ;
	}
}

function getextent()		// Reads metadata from the server
{
	// use form controls to get at values for start and stop dates
	var startyear = document.getElementById('controlform_selectedstartyear').value ;
	var startmonth = document.getElementById('controlform_selectedstartmonth').value ;
	var startday = document.getElementById('controlform_selectedstartday').value ;
	var starthour = document.getElementById('controlform_selectedstarthour').value ;
	var startmin = document.getElementById('controlform_selectedstartmin').value ;
	var startsec = document.getElementById('controlform_selectedstartsec').value ;
	var startdatetime = new Date(startyear,startmonth-1,startday,starthour,startmin,startsec) ;
	var startdatetimestring = startyear+"_"+startmonth+"_"+startday+"_"+starthour+"_"+startmin+"_"+startsec ;	// locale?
	var stopyear = document.getElementById('controlform_selectedstopyear').value ;
	var stopmonth = document.getElementById('controlform_selectedstopmonth').value ;
	var stopday = document.getElementById('controlform_selectedstopday').value ;
	var stophour = document.getElementById('controlform_selectedstophour').value ;
	var stopmin = document.getElementById('controlform_selectedstopmin').value ;
	var stopsec = document.getElementById('controlform_selectedstopsec').value ;
	var stopdatetime = new Date(stopyear,stopmonth-1,stopday,stophour,stopmin,stopsec) ;
	var stopdatetimestring = stopyear+"_"+stopmonth+"_"+stopday+"_"+stophour+"_"+stopmin+"_"+stopsec ;	// locale?
	// Calculate duration from stop-start, check sign and magnitude
	var duration = stopdatetime.getTime() - startdatetime.getTime() ;
	if( (duration <= 0) || (startdatetime == 0) || (stopdatetime == 0) )
	{
		startdatetimestring = "" ;
		stopdatetimestring = "" ;
	}
	var selectedtrack = document.getElementById('controlform_selectedtrack').value ;
	//var selectedoptions = document.getElementById('controlform_selectedoptions').value ;
	// Prepare the server script URL
	var url = "metadata.php?type=extent&start="+startdatetimestring+"&stop="+stopdatetimestring+"&track="+selectedtrack ;
	var randomnumber=Math.floor(Math.random()*100) ;	// Create a 2 digit random number
	url += "&q="+randomnumber ;	// Forces the browser to resubmit the URL
	//alert('debug: getextent: calling ' + url);
	debug.value = 'getextent: url='+url ;
	createProgress("Querying the server for data...") ;	// Display progress information
	progresstimer = setTimeout(timeoutProgress,PROGRESSTIMEOUT) ;	// setup a timeout event do dismiss the progress window after a certain time
	requesting = true ;
	request = GXmlHttp.create();
	request.open("GET", url, true);
	request.onreadystatechange = function()
	{
		if (request.readyState == 4)
		{
			clearTimeout(progresstimer) ;	// Cancel the progress timeout
			requesting = false ;
			var view = null ;
			var message = null ;
			filename = null ;
			if( request.status == 200 )
			{
				var resultText = request.responseText;	//var resultXml = request.responseXml;
				debug.value = 'getextent: resultText='+resultText ;
				// obtain the result contents and process it
				lines = resultText.split("\n") ;
				var linecount = lines.length ;
				if( (lines[0] == "OK") && (linecount > 1) )
				{
					for( var line = 1 ; line < linecount ; line++ )
					{
						args = lines[line].split("=") ;
						argc = args.length ;
						if( argc == 2 )
						{
							//Extent[args[0]] = args[1] ;
							Extent[line] = args[1] ;
						}
					}
					recenterMap(Extent) ;	// Set map view according to boundary values from extent
					resetDates(Extent) ;	// Set form date controls to start and stop dates from extent
					if( TrackList.length == 0 )
					{
						gettracklist() ;	// Load metadata from server, sets track list
					}
				}
				else
				{
					//message = "Server error:\n"+lines[0] ;
				}
			}
			else
			{
				message = "Cannot fetch data from server.\n" ;
			}
			removeProgress() ;	// Cancel the progress window
			if( message != null )
			{
				alert(message) ;
			}
		}
		else
		{
			debug.value = 'getextent: readyState='+request.readyState ;
		}
	}
	request.send(null);
}

function gettracklist()		// Reads metadata from the server, puts up a progress screen while it's busy
{
	//var selectedoptions = document.getElementById('controlform_selectedoptions').value ;
	// Prepare the server script URL
	var url = "metadata.php?type=tracklist" ;
	var randomnumber=Math.floor(Math.random()*100) ;	// Create a 2 digit random number
	url += "&q="+randomnumber ;	// Forces the browser to resubmit the URL
	//alert('debug: gettracklist: calling ' + url);
	debug.value = 'gettracklist: url='+url ;
	createProgress("Querying the server for data...") ;	// Display the progress information 
	progresstimer = setTimeout(timeoutProgress,PROGRESSTIMEOUT) ;	// setup a timeout event do dismiss the progress window after a certain time
	requesting = true ;
	request = GXmlHttp.create();
	request.open("GET", url, true);
	request.onreadystatechange = function()
	{
		if (request.readyState == 4)
		{
			clearTimeout(progresstimer) ;	// Cancel the progress timeout
			requesting = false ;
			var view = null ;
			var message = null ;
			filename = null ;
			if( request.status == 200 )
			{
				var resultText = request.responseText;	//var resultXml = request.responseXml;
				debug.value = 'gettracklist: resultText='+resultText ;
				// obtain the result contents and process it
				lines = resultText.split("\n") ;
				var linecount = lines.length ;
				//debug.value = 'gettracklist: linecount='+linecount ;
				if( (lines[0] == "OK") && (linecount > 1) )
				{
					for( var line = 1 ; line < linecount ; line++ )
					{
						if( lines[line] == undefined )
						{
							continue ;
						}
						if( lines[line].length > 1 )
						{
							TrackList[line] = lines[line] ;	// The entire line contains JUST the track name
						}
					}
					buildtrackcontrols(TrackList) ;	// set form track control from track list
				}
				else
				{
					//message = "Server error:\n"+lines[0] ;
				}
			}
			else
			{
				message = "Cannot fetch data from server.\n" ;
			}
			removeProgress() ;	// Cancel the progress window
			if( message != null )
			{
				alert(message) ;
			}
		}
		else
		{
			debug.value = 'gettracklist: readyState='+request.readyState ;
		}
	}
	request.send(null);
}

function doMakeKML()		// Makes the server generate a KML for the requested data and display options and plot it
{
	// use form controls to get at values for start and stop dates
	var startyear = document.getElementById('controlform_selectedstartyear').value ;
	var startmonth = document.getElementById('controlform_selectedstartmonth').value ;
	var startday = document.getElementById('controlform_selectedstartday').value ;
	var starthour = document.getElementById('controlform_selectedstarthour').value ;
	var startmin = document.getElementById('controlform_selectedstartmin').value ;
	var startsec = document.getElementById('controlform_selectedstartsec').value ;
	var startdatetime = new Date(startyear,startmonth-1,startday,starthour,startmin,startsec) ;
	var startdatetimestring = startyear+"_"+startmonth+"_"+startday+"_"+starthour+"_"+startmin+"_"+startsec ;	// locale?
	var stopyear = document.getElementById('controlform_selectedstopyear').value ;
	var stopmonth = document.getElementById('controlform_selectedstopmonth').value ;
	var stopday = document.getElementById('controlform_selectedstopday').value ;
	var stophour = document.getElementById('controlform_selectedstophour').value ;
	var stopmin = document.getElementById('controlform_selectedstopmin').value ;
	var stopsec = document.getElementById('controlform_selectedstopsec').value ;
	var stopdatetime = new Date(stopyear,stopmonth-1,stopday,stophour,stopmin,stopsec) ;
	var stopdatetimestring = stopyear+"_"+stopmonth+"_"+stopday+"_"+stophour+"_"+stopmin+"_"+stopsec ;	// locale?
	// Calculate duration from stop-start, check sign and magnitude
	var duration = stopdatetime.getTime() - startdatetime.getTime() ;
	if( duration <= 0 )
	{
		var alertstring = "Start time must be before stop time.\nYou asked for:\n" ;
		alertstring += "start at "+startyear+"/"+startmonth+"/"+startday+" "+starthour+":00:00\n" ;
		alertstring += "stop at "+stopyear+"/"+stopmonth+"/"+stopday+" "+stophour+":00:00" ;
		alert(alertstring) ;
		return ;
	}
	var selectedtrack = document.getElementById('controlform_selectedtrack').value ;
	DebugSelectedTrack = document.getElementById('controlform_selectedtrack').value ;
	var selectedoptions = document.getElementById('controlform_selectedoptions').value ;
	//
	// Done with the form controls, let's GO
	//
	// Remove previous coverage overlay, if there is one
	if( geoXmlKml != null )
	{
		map.removeOverlay(geoXmlKml) ;
		geoXmlKml = null ;
	}
	KmlFilename = null ;
	KmlUrl = null ;
	// Prepare the server script URL
	var url = "mkkml.php?start="+startdatetimestring+"&stop="+stopdatetimestring+"&track="+selectedtrack+"&options="+selectedoptions ;
	var randomnumber=Math.floor(Math.random()*100) ;	// Create a 2 digit random number
	url += "&q="+randomnumber ;	// Forces the browser to resubmit the URL
	//alert('debug: doMakeKML: calling ' + url);
	debug.value = 'doMakeKML: url='+url ;
	createProgress("Querying the server for data...") ;	// Display the progress information 
	progresstimer = setTimeout(timeoutProgress,PROGRESSTIMEOUT) ;	// setup a timeout event do dismiss the progress window after a certain time
	requesting = true ;
	request = GXmlHttp.create();
	request.open("GET", url, true);
	request.onreadystatechange = function()
	{
		if (request.readyState == 4)
		{
			clearTimeout(progresstimer) ;	// Cancel the progress timeout
			requesting = false ;
			var view = null ;
			var message = null ;
			filename = null ;
			if( request.status == 200 )
			{
				var resultText = request.responseText;	//var resultXml = request.responseXml;
				debug.value = 'doMakeKML: resultText='+resultText ;
				// obtain the result contents and process it
				lines = resultText.split("\n") ;
				var linecount = lines.length ;
				if( (lines[0] == "OK") && (linecount > 1) )
				{
					args = lines[1].split("=") ;
					if( args[0] == "Filename" )	// args[0] contains the parameter name 'filename'
					{
						filename = args[1] ;	// args[1] contains the parameter value
					} 
					if( (filename == null) || (filename.length == 0) )
					{
						message = "Server error:\nNo filename in server response" ;
					}
				}
				else
				{
					//message = "Server error:\n"+lines[0] ;
				}
			}
			else
			{
				message = "Cannot fetch data from server.\n" ;
			}
			if( filename != null )
			{
				KmlFilename = filename ;			// The filename for the current KML file
				KmlUrl = "http://"+KMLURLROOT+KmlFilename ;	// The URL for the current KML file
				geoXmlKml = new GGeoXml(KmlUrl) ;		// Define new overlay based on KML file at URL
				map.addOverlay(geoXmlKml);			// Display new overlay
				debug.value = 'doMakeKML: KML url='+KmlUrl ;
				// Deleted all the view setting code, the coverage map should not determine the view
			}
			removeProgress() ;	// Cancel the progress window
			if( message != null )
			{
				alert(message) ;
			}
		}
		else
		{
			debug.value = 'doMakeKML: readyState='+request.readyState ;
		}
	}
	request.send(null) ;
}

function doFit()
{
	getextent() ;
}

function doDebug()		// This runs whenever the user presses the Debug button
{
	//showExtent() ;
	//showTrackList() ;
	alert("selectedtrack="+document.getElementById('controlform_selectedtrack').value) ;
}

//END

