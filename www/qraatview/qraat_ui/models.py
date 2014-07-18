# File: qraat_ui/models.py

from django.db import models

QRAAT_APP_LABEL = 'qraat_ui'


class Position(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        unique_together = (
            "ID", "deploymentID", "timestamp")  # set multiple fields as keys
        db_table = "position"

    ID = models.AutoField(primary_key=True)
    deploymentID = models.BigIntegerField()  # secondary key
    timestamp = models.DecimalField(
        max_digits=16, decimal_places=6)  # decimal(16,6) secondary key
    easting = models.DecimalField(
        max_digits=9, decimal_places=2)  # decimal(9,2)
    northing = models.DecimalField(
        max_digits=10, decimal_places=2)  # decimal(10,2)
    utm_zone_number = models.SmallIntegerField(
        default=10)  # tinyint(3) default 10
    utm_zone_letter = models.CharField(
        default='S', max_length=1)  # varchar(1) default S
    likelihood = models.FloatField()  # double
    activity = models.FloatField()  # double

class Deployment(models.Model):
  class Meta:
    app_label = QRAAT_APP_LABEL
    unique_together = ("ID", "txID", "targetID", "projectID")
    db_table = "deployment"

  ID = models.AutoField(primary_key=True)
  name = models.CharField(max_length=50)
  description = models.TextField()
  time_start = models.DecimalField(max_digits=16, decimal_places=6)
  time_end = models.DecimalField(max_digits=16, decimal_places=6)
  txID =  models.SmallIntegerField(max_length=10)
  targetID = models.SmallIntegerField(max_length=10)
  projectID = models.SmallIntegerField(max_length=10)
  is_active = models.SmallIntegerField(max_length=10, default=0)
  is_hidden = models.SmallIntegerField(max_length=10, default=0)


class Site(models.Model):
  class Meta:
    app_label = QRAAT_APP_LABEL
    db_table = "site"
  
  ID = models.AutoField(primary_key=True)
  name = models.CharField(max_length=20)
  location = models.CharField(max_length=100)
  latitude = models.DecimalField(max_digits=10, decimal_places=6)
  longitude = models.DecimalField(max_digits=11, decimal_places=6)
  easting = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
  northing = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
  utm_zone_number = models.SmallIntegerField(max_length=3, default=10)
  utm_zone_letter = models.CharField(max_length=1, default='S')
  elevation = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)

class track(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "track"
        unique_together = ("ID", "depID")

    SPEED_CHOICES = (('1', 'exp'), ('2', 'linear'), ('3', 'const'))

    ID = models.AutoField(primary_key=True)
    depID = models.BigIntegerField(max_length=20)
    max_speed_family = models.CharField(
        max_length=1, choices=SPEED_CHOICES)  # enum('exp','linear','const')
    speed_burst = models.FloatField()
    speed_sustained = models.FloatField()
    speed_limit = models.FloatField()

    def __unicode__(self):
        return u'%s' % self.ID
