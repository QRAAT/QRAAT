import json
import calendar
import decimal
from dateutil.tz import tzlocal
from datetime import datetime
from django.db.models.base import ModelState


def timestamp_todate(timestamp):
    return datetime.fromtimestamp(
        int(timestamp)).strftime("%m/%d/%Y %H:%M:%S")


def date_totimestamp(date):
    try:
        timestamp = calendar.timegm(date.timetuple())
    except Exception, e:
        raise e
    else:
        return timestamp


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
