# File: models.py

from django.db import models

QRAAT_APP_LABEL = 'hello'


class Position(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        unique_together = (
            "ID", "depID", "timestamp")  # set multiple fields as keys
        db_table = "Position"

    ID = models.AutoField(primary_key=True)
    depID = models.BigIntegerField()  # secondary key
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


class TxType(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_type"

    ID = models.AutoField(primary_key=True)
    RMG_type = models.CharField(max_length=20)  # varchar(20)
    tx_table_name = models.CharField(max_length=30)  # varchar(30)

    def __unicode__(self):
        return u'%d' % self.ID


class TxInfo(models.Model):
        class Meta:
            app_label = QRAAT_APP_LABEL
            db_table = "tx_info"

        ID = models.AutoField(primary_key=True)
        tx_type_ID = models.ForeignKey(
            TxType, db_column="tx_type_ID")  # One to One relation with tx_type
        manufacturer = models.CharField(max_length=50)  # varchar(50)
        model = models.CharField(max_length=50)  # varchar(50)

        def __unicode__(self):
            return u'%d %s' % (self.ID, self.model)


class tx_ID(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_ID"

    ID = models.AutoField(
        primary_key=True)  # int(10) primary key autoincrement
    tx_info_ID = models.ForeignKey(
        TxInfo, db_column="tx_info_ID")  # foreignKey from tx_info
    active = models.BooleanField(default=False)  # tinyint(1)

    def __unicode__(self):
        return u'%d' % self.ID


class TxPulse(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_pulse"

    tx_ID = models.ForeignKey(tx_ID, primary_key=True, db_column="tx_ID")
    frequency = models.FloatField()  # float
    pulse_width = models.FloatField()  # float
    pulse_rate = models.FloatField()  # float
    band3 = models.SmallIntegerField()  # small integer
    band10 = models.SmallIntegerField()  # small integer


class TxAlias(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_alias"

    ID = models.AutoField(primary_key=True)
    tx_ID = models.ForeignKey(tx_ID, db_column="tx_ID")
    alias = models.CharField(max_length=50)  # varchar(50)


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

class sitelist(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "sitelist"

    ID = models.AutoField(primary_key=True)  # int(11), auto_increment
    name = models.CharField(max_length=20)  # varchar(20)

    location = models.CharField(max_length=100)  # varchar(100)

    latitude = models.DecimalField(
        max_digits=10, decimal_places=6)  # decimal(10,6)

    longitude = models.DecimalField(
        max_digits=10, decimal_places=6)  # decimal(11,6)

    easting = models.DecimalField(
        default=0.00, max_digits=9, decimal_places=2)  # decimal(9,2) unsigned

    northing = models.DecimalField(
        default=0.00, max_digits=10,
        decimal_places=2)  # decimal(10,2) unsigned

    utm_zone_number = models.SmallIntegerField(
        default=10)  # tinyint(3) unsigned, default 10

    utm_zone_letter = models.CharField(
        default='S', max_length=1)  # char(1), default S

    elevation = models.DecimalField(
        default=0.00, max_digits=7,
        decimal_places=2)  # decimal(7,2), default 0.00

    rx = models.SmallIntegerField(default=1)  # tinyint(1), default 1

    def __unicode__(self):
        return u'%s' % self.name
