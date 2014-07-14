# File: qraat_site models.py

from django.db import models

QRAAT_APP_LABEL = 'qraat_site'


class RxSite(models.Model):
    """ Site data (public)
        only sites with receivers, admins are the only ones with write access
    """

    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "rx_site"

    ID = models.AutoField(primary_key=True)

    name = models.CharField(max_length=20)  # varchar(20)

    location = models.CharField(max_length=100)  # varchar(100)

    latitude = models.DecimalField(
        max_digits=10, decimal_places=6)  # decimal(10, 6)

    longitude = models.DecimalField(
        max_digits=11, decimal_places=6)  # decimal(11,6)

    easting = models.DecimalField(
        max_digits=9, decimal_places=2, default=0.00)  # decimal(9,2)

    northing = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)  # decimal(10, 2)

    utm_zone_number = models.SmallIntegerField(
        max_length=3, default=10)  # tinyint(3) default 10

    utm_zone_letter = models.CharField(
        max_length=1, default='S')  # char(1) default S

    elevation = models.DecimalField(
        max_digits=7, decimal_places=2,
        default=0.00)  # decimal(7, 2) default 0.00


class Project(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "project"

    ID = models.AutoField(primary_key=True)

    ownerID = models.IntegerField(null=False, help_text="References UID in\
                                  web frontend, i.e 'django.auth_user.id'")

    name = models.CharField(max_length=50, null=False)  # varchar(50) not null

    description = models.TextField()

    is_public = models.SmallIntegerField(
        max_length=1, null=False)  # tinyint(1) not nul


class AuthProjectViewer(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "auth_project_viewer"

    ID = models.AutoField(primary_key=True)

    groupID = models.IntegerField(
        null=False,
        help_text="References GUID in web forntend, i.e. django.auth_group.id")

    projectID = models.ForeignKey(Project, db_column="projectID")


class AuthProjectCollaborator(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "auth_project_collaborator"

    ID = models.AutoField(primary_key=True)

    groupID = models.IntegerField(
        null=False,
        help_text="References GUID in web frontend, i.e. django.auth.group.id")

    projectID = models.ForeignKey(Project, db_column="projectID")


class Position(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        unique_together = (
            "ID", "deploymentID", "timestamp")  # set multiple fields as keys
        db_table = "position"

    ID = models.AutoField(primary_key=True)

    deploymentID = models.BigIntegerField(null=False)  # secondary key not null

    timestamp = models.DecimalField(
        null=False, max_digits=16,
        decimal_places=6)  # decimal(16,6) secondary key

    latitude = models.DecimalField(
        max_digits=10, decimal_places=6)  # decimal(10, 6)

    longitude = models.DecimalField(
        max_digits=11, decimal_places=6)  # decimal(11, 6)

    easting = models.DecimalField(
        null=False, max_digits=9, decimal_places=2,
        help_text="Most likely position (UTM east).")  # decimal(9,2)

    northing = models.DecimalField(
        null=False, max_digits=10, decimal_places=2,
        help_text="Most likely position (UTM north).")  # decimal(10,2)

    utm_zone_number = models.SmallIntegerField(
        default=10,
        help_text="Most likely position (UTM zone).")  # tinyint(3) default 10

    utm_zone_letter = models.CharField(
        default='S', max_length=1,
        help_text="Most likely position\
                (UTM zone letter).")  # varchar(1) default S

    likelihood = models.FloatField(
        null=False,
        help_text="Maximum likelihood value over search space.")  # double

    activity = models.FloatField(
        help_text="Averaged over bearing data from all sites")  # double


class TxInfo(models.Model):
        class Meta:
            app_label = QRAAT_APP_LABEL
            db_table = "tx_info"

        ID = models.AutoField(primary_key=True)
        manufacturer = models.CharField(max_length=50)  # varchar(50)
        model = models.CharField(max_length=50)  # varchar(50)

        def __unicode__(self):
            return u'%d %s' % (self.ID, self.model)


class Tx(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx"

    DEMOD_CHOICES = (
        ("pulse", "pulse"), ("cont", "cont"), ("afsk", "afsk"))

    ID = models.AutoField(
        primary_key=True)  # int(10) primary key autoincrement

    tx_infoID = models.ForeignKey(
        TxInfo, db_column="tx_infoID")  # foreignKey from tx_info

    projectID = models.ForeignKey(
        Project, db_column="projectID")

    frequency = models.FloatField()

    demod_type = models.CharField(max_length=5, choices=DEMOD_CHOICES)

    def __unicode__(self):
        return u'%d' % self.ID


class TxParameters(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_parameters"
        unique_together = ("ID", "txID", "name")  # set multiple fields as keys

    ID = models.AutoField(max_length=10, primary_key=True)

    txID = models.ForeignKey(Tx, db_column="txID")

    name = models.CharField(max_length=32)  # varchar(32)

    value = models.CharField(max_length=64)  # varchar(64)


class Target(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "target"

    ID = models.AutoField(
        primary_key=True,
        max_length=10)  # primary_key auto-increment int(10)

    name = models.CharField(max_length=50)

    description = models.TextField()  # text

    projectID = models.ForeignKey(
        Project, db_column="projectID",
        help_text="Project for which target was originally created")


class Deployment(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "deployment"

    ID = models.AutoField(max_length=10, primary_key=True)

    name = models.CharField(max_length=50)

    description = models.TextField()

    txID = models.ForeignKey(
        Tx, db_column="txID")

    targetID = models.ForeignKey(
        Target, db_column="targetID")

    projectID = models.ForeignKey(
        Project, db_column="projectID")

    time_start = models.DecimalField(
        max_digits=16, decimal_places=6)  # decimal(16,6)

    time_end = models.DecimalField(
        max_digits=16, decimal_places=6)  # decimal(16,6)


class Track(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "track"

    SPEED_CHOICES = (('exp', 'exp'), ('linear', 'linear'), ('const', 'const'))

    ID = models.AutoField(primary_key=True)

    deploymentID = models.ForeignKey(
        Deployment, db_column="deploymentID")

    projectID = models.ForeignKey(Project, db_column="projectID")

    max_speed_family = models.CharField(
        max_length=6, choices=SPEED_CHOICES)  # enum('exp','linear','const')

    speed_burst = models.FloatField()

    speed_sustained = models.FloatField()

    speed_limit = models.FloatField()

    def __unicode__(self):
        return u'%s' % self.ID


class Site(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "site"

    ID = models.AutoField(primary_key=True)  # int(11), auto_increment

    projectID = models.ForeignKey(Project, db_column="projectID")

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

    def __unicode__(self):
        return u'%s' % self.name
