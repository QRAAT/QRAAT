from datetime import datetime


def timestamp_todate(timestamp):
    return datetime.fromtimestamp(
        int(timestamp)).strftime("%m/%d/%Y %H:%M:%S")
