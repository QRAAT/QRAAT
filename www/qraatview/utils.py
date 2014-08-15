import json
import time
import decimal
from datetime import datetime
from django.db.models.base import ModelState


def timestamp_todate(timestamp):
    return datetime.fromtimestamp(
        int(timestamp)).strftime("%m/%d/%Y %H:%M:%S")


def date_totimestamp(date):
    try:
        timestamp = time.mktime(date.timetuple())
    except Exception, e:
        raise e
    else:
        return timestamp


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, ModelState):
            return None
        else:
            return json.JSONEncoder.default(self, obj)
