#!/usr/bin/env python
"""RESTFul api that handles http request and mounts a Django's QuerySet.

This module is the core of a RESTFul api, it can serialize data,
but doesn't render any data. Data render are placed in the views.
"""

import pytz
from django.db.models import get_app, get_models
from django.db.models.fields import DecimalField, DateTimeField
from django.core import serializers
from django.utils import timezone
from dateutil.tz import tzlocal
from dateutil import parser
import utils

__author__ = "Jeymisson Oliveira"
__copyright__ = ""
__credits__ = ["Jeymisson Oliveira"]

__license__ = ""
__version__ = "1.0"
__maintainer__ = ""
__email__ = ""
__status__ = "Production"


def json_parse(data):
    """This function serializes to json Django's\
            QuerySet or Django's ValuesQuerySet

    :param data: Django's QuerySet of Djago's ValuesQuerySet
    :type data: QuerySet.
    :returns:  str - Json serialized data
    :raises: TypeError, Exeption
    """

    if data is not None:
        try:
            return serializers.serialize("json", data)
        except AttributeError:
            return list(data)
        except Exception, e:
            raise e
    else:
        raise TypeError("Can't serialize a None type")


def filter_by_date(
        model, date_obj, start_date, end_date, duration):
    """Creates django's filters for given date or interval

    :param model: obj where filter will be applied
    :type model: str.
    :param date_obj: database table where the requested data is
    :type date_obj: str.
    :param start_date: string start_date
    :type start_date: str.
    :param end_date: string end_date
    :type end_date: str.
    :param duration: Time interval in days.
    :type duration: str.
    :returns: dict -- A dictionary with django's query filters
    """

    dic_filter = {}
    obj = utils.get_field_instance(model, date_obj)

    if obj:
        DATE_PATTERN = "%m/%d/%Y %H:%M:%S"
        tz = tzlocal()

        start_date_filter = {}
        end_date_filter = {}

        # Apply default case, query from yesterday to now
        if not start_date:
            yesterday = timezone.now() - timezone.timedelta(1)
            start_date = yesterday.strftime(DATE_PATTERN)
        if not end_date:
            end_date = "now"

        start_date = parser.parse(start_date).replace(tzinfo=tz)

        if end_date.lower() == 'now':
            end_date = timezone.now()
        else:
            end_date = parser.parse(end_date).replace(tzinfo=tz)

        # handle duration case
        if duration:
            start_date -= utils.get_timedelta(duration)

        # handle different field instances: timestamp, datetime
        if isinstance(obj, DateTimeField):
            start_date = start_date
            end_date = end_date

        elif isinstance(obj, DecimalField):
            start_date = utils.date_totimestamp(
                start_date.astimezone(pytz.utc))
            end_date = utils.date_totimestamp(end_date.astimezone(pytz.utc))

        start_date_filter[date_obj + "__gte"] = start_date
        end_date_filter[date_obj + "__lte"] = end_date

        dic_filter.update(start_date_filter)
        dic_filter.update(end_date_filter)

    return dic_filter


def filter_databy_id(ids):
    """Filters data by given ids

    :param ids: list of obj ids to be selected
    :type ids: list.
    :returns:  dict -- Django's QuerySet filter
    """

    dict_filter = {}
    dict_filter["ID__in"] = ids
    return dict_filter


def filter_databy_field(fields, data):
    """Filters data by given fields

    :param fields: list of obj's fields
    :type fields: list.
    :param data: Django's QuerySet with previous data selected
    :type data: QuerySet.
    :returns:  ValuesQuerySet. -- Django's ValuesQuerySet obj
    """

    return data.values(*fields)


def get_subset(data, n_items):
    """Function to subset a dataset

    :param data: Django's QuerySet with previous data selected
    :type data: QuerySet.
    :param n_items: desired set's size
    :type n_items: int.
    :returns: QuerySet -- A queryset's subset of size ``n_items``
    """

    return data[:n_items]


def get_offset(data, offset):
    """Function to offset a dataset

    :param data: Django's QuerySet with previous data selected
    :type data: QuerySet.
    :param offset: Offset's size
    :type offset: int.
    :returns: QuerySet -- Subset of original queryset from offset to last item
    """

    return data[offset:]


def get_distinct_data(data, distinct):
    """Function to eliminate repeated data

    :param data: Django's QuerySet with previous data selected
    :type data: QuerySet.
    :param distinct: The field name that should not have repeated values
    :type distinct: str.
    :returns: QuerySet -- A queryset without repeated values for\
            the ``distinct`` field entered
    """

    return data.values(*distinct).distinct()


def filter_datafor_field(filter_field):
    """Filters data for specific field's value

    :param filter_field: Field's name and value in the respective\
            format "**field_name,field_value**"
    :type filter_field: str.
    :returns: dict -- Django's queryset filter. Corresponds to\
            SELECT * FROM tableX WHERE **field_name=field_value**
    """

    dict_filter = {}
    for f in filter_field:
        field, f_filter = f.split(",")

        dict_filter[field] = f_filter

    return dict_filter


def get_model_data(request):
    """Main api function that retrieves Django's
    data selected by a get request. This function is called by
    views in qraatview and qraat_ui
    
    :param request: Request generally made by a call to a view
    :type request: HttpRequest.
    :returns: QuerySet -- Django's queryset with selected filters applied
    """

    obj_type = request.GET.get("obj")
    ids = request.GET.getlist("id")
    fields = request.GET.getlist("field")
    n_items = request.GET.get("n_items")
    offset = request.GET.get("offset")
    distinct = request.GET.getlist("distinct")
    filter_field = request.GET.getlist("filter_field")
    date_obj = request.GET.get("date")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    duration = request.GET.get("duration")

    model = get_model_type(obj_type)
    dict_filter = {}

    if filter_field:
        dict_filter.update(filter_datafor_field(filter_field))

    if date_obj:
        dict_filter.update(
            filter_by_date(model, date_obj, start_date, end_date, duration))

    if ids:
        dict_filter.update(filter_databy_id(ids))

    # select data
    data = model.objects.filter(**dict_filter)

    # strip data
    if fields:
        if(ids):
            fields.append(u'ID')
        data = filter_databy_field(fields, data)

    if distinct:
        data = get_distinct_data(data, distinct)

    if offset:
        data = get_offset(data, offset)

    if n_items:
        data = get_subset(data, n_items)

    return data


def get_model_type(model_type):
    """This function is for intern use. It gets
    a model instance based on it's verbose name

    :param model_type: Model's type name that will be looked up
    :type model_type: str.
    :returns: Model -- qraatview Django's model instance
    """

    app = get_app("qraatview")
    if model_type is not None:
        for model in get_models(app):
            if model._meta.verbose_name.lower() == model_type.lower():
                return model
    return None
