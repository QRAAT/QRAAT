#!/usr/bin/env python2
"""QRAAT View utils model.

Here is encapsulated functions to handle and parse dates
and any other function that is part of qraatview project
"""

import json
import calendar
import decimal
# TODO: Get rid of dateutil for pytz once date_totimestamp is figured out
from dateutil.tz import tzlocal 
import pytz
from datetime import datetime, timedelta
from django.db.models.base import ModelState
import gaat.timezoneinfo

__author__ = "Jeymisson Oliveira"
__copyright__ = ""
__credits__ = ["Jeymisson Oliveira"]

__license__ = ""
__version__ = "1.0"
__maintainer__ = ""
__email__ = ""
__status__ = "Production"

DATA_TIMEZONE = pytz.timezone(gaat.timezoneinfo.TIMEZONE)
''' 
The following couple functions, up to but not including def date_totimestamp, is written with the assumption that by 'local' we mean local to our data.
At the time of writing, we only have data from one location, in one timezone. 
That timezone is specified in the timezoneinfo file as a string.
Specifying the timezone instead of using local datetime functions may be redundant if your server is in the same timezone as your data, but doing so allows your server to be anywhere and allows easier extensibility if there's data from other locations.
'''

def strftime(date, PATTERN = "%Y-%m-%d %H:%M:%S"):
    return date.strftime(PATTERN)

# Returns a naive datetime
def strptime(date_string, PATTERN = "%Y-%m-%d %H:%M:%S"):
    try:
        return datetime.strptime(date_string, PATTERN)
    except Exception, e:
        raise e

def get_local_now():
    return DATA_TIMEZONE.normalize(pytz.utc.localize(datetime.utcnow()))

''' UTC timestamp to Los Angeles (DATA_TIMEZONE) datetime

Use tz.localize(datetime) instead of datetime.replace(tzinfo=tz) for naive datetime to get the right result with pytz timezones
You can use datetime.astimezone(tz) or tz.normalize(datetime) to convert an aware datetime to another timezone
Using replace() seems to give the wrong result, b/c many timezones in pytz use the old LMT timezones which is 7/8 minutes off of todays. http://www.gossamer-threads.com/lists/python/python/1189541#1189541
 '''
def timestamp_todate(timestamp):
    #return datetime.fromtimestamp(
    #    float(timestamp)).replace(tzinfo=tzlocal())
    # is_dst=True only makes a difference when a time is ambiguous; IE, there's time overlap because of daylight saving. When that is the case, is_dst=True will select the earlier time so we dont skip data because of dst.
    try:
        return DATA_TIMEZONE.normalize(pytz.utc.localize(datetime.utcfromtimestamp(float(timestamp)), is_dst=True).astimezone(DATA_TIMEZONE))
    except Exception, e:
        raise e

''' Converts a local datetime to a timestamp. 
If a naive datetime is passed in, it assumes it is in local time, and gives it tz info.
If an aware date is passed in, it checks if it's the right locale
'''
def datelocal_totimestamp(date):
    if(date.tzinfo == None): # Naive time: timegm expects UTC/GMT time
        try:
            return calendar.timegm(pytz.utc.normalize(DATA_TIMEZONE.localize(date)).timetuple())
        except Exception, e:
            raise e
    else: # Aware: must be in the DATA_TIMEZONE
        if date.tzinfo.zone != DATA_TIMEZONE.zone:
            raise ValueError('Aware datetime timezone is not DATA_TIMEZONE')
        else: 
            try:
                return calendar.timegm(pytz.utc.normalize(date).timetuple())
            except Exception, e:
                raise e

# TODO: Is date expected to be in UTC or local? Delete this if it turns out to be the same as above
def date_totimestamp(date): 
    try:
        timestamp = calendar.timegm(date.timetuple())
    except Exception, e:
        raise e
    else:
        return timestamp


def get_timedelta(duration):
    """Given a duration interval returns a timedelta object that represents
    this duration"""

    DAY, WEEK, MONTH, YEAR = 1, 7, 30, 365
    duration_time = None

    if isinstance(duration, str):
        duration = duration.lower()

    if duration == 'day':
        duration_time = timedelta(days=DAY)

    elif duration == 'week':
        duration_time = timedelta(days=WEEK)

    elif duration == 'month':
        duration_time = timedelta(days=MONTH)

    elif duration == 'year':
        duration_time = timedelta(days=YEAR)

    else:
        if isinstance(duration, int):
            duration_time = timedelta(days=duration)

    return duration_time


def get_field_instance(model, field_name):
    """This function gets a field instance based on it's verbose name
    
    :param model: Model that contains the field
    :type model: Model.
    :param field_name: field verbose name
    :type field_name: str.
    :returns: Field -- Django's field instance
    """

    for field in model._meta.fields:
        if field_name == field.verbose_name:
            return field


class DateTimeEncoder(json.JSONEncoder):
    """Adapter class that encodes a datetime object to json object"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return date_totimestamp(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, ModelState):
            return None
        else:
            return json.JSONEncoder.default(self, obj)
