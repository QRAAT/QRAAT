import json
import calendar
import decimal
from dateutil.tz import tzlocal
from datetime import datetime, timedelta
from django.db.models.base import ModelState


def strfdate(date):
    PATTERN = "%m/%d/%Y %H:%M:%S"
    return date.strftime(PATTERN)


def timestamp_todate(timestamp):
    return datetime.fromtimestamp(
        float(timestamp)).replace(tzinfo=tzlocal())


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
