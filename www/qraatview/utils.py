from datetime import datetime
import time


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
