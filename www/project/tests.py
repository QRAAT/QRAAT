from django.test import TestCase
import datetime
import pytz
from dateutil.tz import tzlocal
from dateutil import parser
from models import Project, Target, Tx, TxMake
from project import utils


class ProjectTestCase(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(ownerID=1, is_public=0)

    def test_create_project(self):
        project1 = Project.objects.get(pk=self.project1.pk)

        self.assertEquals(
            project1, self.project1, msg="Projects are different")

    def test_project_public(self):
        project = Project.objects.create(ownerID=1, is_public=1)
        self.assertEquals(1, project.is_public)


class TransmitterTestCase(TestCase):

    def setUp(self):
        self.project = Project.objects.create(ownerID=1, is_public=0)

    def test_create_Tx(self):
        tx_make = TxMake.objects.create(
            manufacturer="Ben Kamen",
            model="Tune-able Transmitter",
            demod_type='pulse')
        tx = Tx.objects.create(projectID=self.project, tx_makeID=tx_make)

        db_tx_make = TxMake.objects.get(pk=tx_make.pk)
        db_tx = Tx.objects.get(pk=tx.pk)

        self.assertEquals(db_tx_make, db_tx, msg="Tx make are different")
        self.assertEquals(tx, db_tx, msg="Tx are different")


class TestUtils(TestCase):
    def setUp(self):
        # Timestamp error of 1 milisecond
        self.error = 0.001
        # Date error 1 second fromtimestamp doesn't return microseconds
        self.date_error = datetime.timedelta(seconds=1)
        # timezones
        self.utc = pytz.utc
        self.local_tz = tzlocal()

    def test_timestamp_todate(self):
        timestamp = 1000401040.0
        local_time = utils.timestamp_todate(timestamp)
        utc_time = local_time.astimezone(self.utc)

        self.assertEquals(utc_time, local_time, "Different times")

        date_to_timestamp = utils.date_totimestamp(utc_time)

        self.assertLessEqual(
            timestamp - date_to_timestamp,
            self.error,
            "Error in conversion from date to timestamp")

    def test_date_totimestamp(self):
        local_date = parser.parse(
            "12/31/2011 23:50").replace(tzinfo=self.local_tz)
        utc_date = local_date.astimezone(tz=self.utc)

        self.assertEquals(local_date, utc_date, "Different dates")

        timestamp = utils.date_totimestamp(utc_date)
        local_from_timestamp = utils.timestamp_todate(timestamp)

        self.assertLessEqual(
            local_date - local_from_timestamp,
            self.date_error,
            "Error in conversion from timestamp to date")
