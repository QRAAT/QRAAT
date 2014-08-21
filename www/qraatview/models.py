# File: qraat_site models.py

from django.db import models
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from utils import timestamp_todate, strfdate

QRAAT_APP_LABEL = 'qraatview'
COLLABORATOR_PERMISSIONS = (
    ("can_change", "Users can change the project data"),
    ("can_hide", "Users can hide a project"))
VIEWER_PERMISSIONS = (
    ("can_view", "Users can view the project data"),)


class Site(models.Model):
    """ Site data (public)
        only sites with receivers, admins are the only ones with write access
    """

    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "site"

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

    def __unicode__(self):
        return u'%s' % self.name


class Project(models.Model):

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
        self._collaborator_permissions = COLLABORATOR_PERMISSIONS
        self._viewer_permissions = VIEWER_PERMISSIONS

    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "project"
        permissions = COLLABORATOR_PERMISSIONS + VIEWER_PERMISSIONS
    
    ID = models.AutoField(primary_key=True)

    ownerID = models.IntegerField(
        null=False, help_text="References UID in\
                                  web frontend, i.e 'django.auth_user.id'")

    name = models.CharField(max_length=50, null=False)  # varchar(50) not null

    description = models.TextField()

    is_public = models.BooleanField(
        default=False, null=False)  # tinyint(1) not nul

    is_hidden = models.BooleanField(default=False)  # boolean default false

    def add_collaborator_permissions(self, group):
        [group.permissions.add(permission)
            for permission in map(
                lambda p: Permission.objects.get(codename=p[0]),
                              (self._collaborator_permissions
                                  + self._viewer_permissions))]

    def add_viewers_permissions(self, group):
        [group.permissions.add(permission)
            for permission in map(
                lambda p: Permission.objects.get(
                    codename=p[0]), self._viewer_permissions)]

    def get_locations(self):
        return Location.objects.filter(
            projectID=self.ID).exclude(is_hidden=True)

    def get_deployments(self):
        return Deployment.objects.filter(
            projectID=self.ID).exclude(is_hidden=True).order_by('-is_active')

    def get_transmitters(self):
        return Tx.objects.filter(projectID=self.ID).exclude(is_hidden=True)

    def get_targets(self):
        return Target.objects.filter(projectID=self.ID).exclude(is_hidden=True)

    def create_viewers_group(self):
        try:
            group = Group.objects.create(
                name="%d_viewers" % self.ID)

        except Exception, e:
            raise e

        else:
            AuthProjectViewer.objects.create(
                groupID=group.id,
                projectID=self)

        return group

    def create_collaborators_group(self):
        try:
            group = Group.objects.create(
                name="%d_collaborators" % self.ID)
        except Exception, e:
            raise e

        else:
            AuthProjectCollaborator.objects.create(
                groupID=group.id, projectID=self)
        return group

    def get_group(self, group_id):
        return Group.objects.get(id=group_id)

    def get_viewers_group(self):
        try:
            group_id = AuthProjectViewer.objects.get(projectID=self.ID).groupID
        except ObjectDoesNotExist:  # for some reason group wasn't created
            group_id = self.create_viewers_group().id

        return self.get_group(group_id)

    def get_collaborators_group(self):
        try:
            group_id = AuthProjectCollaborator.objects.get(
                projectID=self.ID).groupID
        except ObjectDoesNotExist:
            group_id = self.create_collaborators_group().id

        return self.get_group(group_id)

    def is_owner(self, user):
        return user.id == self.ownerID

    def is_collaborator(self, user):
        return user in self.get_collaborators_group().user_set.all()

    def is_viewer(self, user):
        return user in self.get_viewers_group().user_set.all()

    def set_permissions(self, group):
        if group == self.get_viewers_group():
            self.add_viewers_permissions(group)
        elif group == self.get_collaborators_group():
            self.add_collaborator_permissions(group)

    def __unicode__(self):
        return u'ID = %d name = %s' % (self.ID, self.name)


class AuthProjectViewer(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "auth_project_viewer"

    ID = models.AutoField(primary_key=True)

    groupID = models.IntegerField(
        null=False,
        unique=True,
        help_text="References GUID in web forntend, i.e. django.auth_group.id")

    projectID = models.ForeignKey(Project, db_column="projectID", unique=True)


class AuthProjectCollaborator(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "auth_project_collaborator"

    ID = models.AutoField(primary_key=True)

    groupID = models.IntegerField(
        null=False,
        unique=True,
        help_text="References GUID in web frontend, i.e. django.auth.group.id")

    projectID = models.ForeignKey(Project, db_column="projectID", unique=True)


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


class TxMake(models.Model):
        class Meta:
            app_label = QRAAT_APP_LABEL
            db_table = "tx_make"

        DEMOD_CHOICES = (
            ("pulse", "pulse"), ("cont", "cont"), ("afsk", "afsk"))

        ID = models.AutoField(primary_key=True)

        manufacturer = models.CharField(max_length=50)  # varchar(50)

        model = models.CharField(max_length=50)  # varchar(50)

        demod_type = models.CharField(max_length=5, choices=DEMOD_CHOICES)

        def __unicode__(self):
            return u'%d %s %s' % (self.ID, self.manufacturer, self.model)


class Tx(models.Model):
    class Meta:
        verbose_name = "Transmitter"
        app_label = QRAAT_APP_LABEL
        db_table = "tx"

    ID = models.AutoField(
        primary_key=True)  # primary key autoincrement

    name = models.CharField(max_length=50, null=False)  # varchar(50) not null

    serial_no = models.CharField(
        max_length=50, null=False)  # varchar(50) not null

    tx_makeID = models.ForeignKey(
        TxMake, db_column="tx_makeID")  # foreignkey from

    projectID = models.ForeignKey(
        Project, db_column="projectID")

    frequency = models.FloatField()

    is_hidden = models.BooleanField(default=False)

    def verbose_name(self):
        return self._meta.verbose_name

    def hide(self):
        objs_related = self.get_objs_related()

        for obj in objs_related:
            obj.hide()

        self.is_hidden = True
        self.save()

    def get_objs_related(self):
        objs_related = Deployment.objects.exclude(
            is_hidden=True).filter(txID=self)
        return objs_related

    def __unicode__(self):
        return u'%s %s' % (self.name, self.serial_no)


class TxParameters(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_parameters"
        unique_together = ("ID", "txID", "name")  # set multiple fields as keys
        verbose_name_plural = "Tx Parameters"

    ID = models.AutoField(primary_key=True)

    txID = models.ForeignKey(Tx, db_column="txID")

    name = models.CharField(max_length=32, null=False)  # varchar(32)

    value = models.CharField(max_length=64, null=False)  # varchar(64)

    units = models.CharField(max_length=32)  # varchar(32)


class TxMakeParameters(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "tx_make_parameters"
        unique_together = ('ID', 'tx_makeID', 'name')
        verbose_name_plural = "Tx Make Parameters"

    ID = models.AutoField(primary_key=True)

    tx_makeID = models.ForeignKey(TxMake, db_column="tx_makeID")

    name = models.CharField(max_length=32, null=False)  # varchar(32)

    value = models.CharField(max_length=64, null=False)  # varchar(64)

    units = models.CharField(max_length=32)  # varchar(32)


class Target(models.Model):
    class Meta:
        verbose_name = "Target"
        app_label = QRAAT_APP_LABEL
        db_table = "target"

    ID = models.AutoField(
        primary_key=True)  # primary_key auto-increment int(10)

    name = models.CharField(max_length=50)

    description = models.TextField()  # text

    projectID = models.ForeignKey(
        Project, db_column="projectID",
        help_text="Project for which target was originally created")

    is_hidden = models.BooleanField(default=False)  # boolean default false

    def verbose_name(self):
        return self._meta.verbose_name

    def hide(self):
        objs_related = self.get_objs_related()

        for obj in objs_related:
            obj.hide()

        self.is_hidden = True
        self.save()

    def get_objs_related(self):
        objs_related = Deployment.objects.exclude(
            is_hidden=True).filter(targetID=self)
        return objs_related

    def __unicode__(self):
        return u'%s' % self.name


class Deployment(models.Model):
    class Meta:
        app_label = QRAAT_APP_LABEL
        db_table = "deployment"

    ID = models.AutoField(primary_key=True)

    name = models.CharField(max_length=50, null=False)

    description = models.TextField(blank=True)

    time_start = models.DecimalField(
        max_digits=16, decimal_places=6,
        help_text="Unix Timestamp (s.us)")  # decimal(16,6)

    time_end = models.DecimalField(
        max_digits=16, decimal_places=6,
        help_text="Unix Timestamp (s.us)",
        blank=True)  # decimal(16,6)

    txID = models.ForeignKey(
        Tx, db_column="txID")

    targetID = models.ForeignKey(
        Target, db_column="targetID")

    projectID = models.ForeignKey(
        Project, db_column="projectID",
        help_text="Project to which deployment is associated.")

    is_active = models.BooleanField(default=False)

    is_hidden = models.BooleanField(default=False)

    def get_objs_related(self):
        return []

    def hide(self):
        related_objs = self.get_objs_related()
        for obj in related_objs:
            obj.hide()

        self.is_hidden = True
        # when a deployment is hidden it is unactive
        self.is_active = False
        self.save()

    def verbose_name(self):
        return self._meta.verbose_name

    def get_start(self):
        return strfdate(timestamp_todate(self.time_start))

    def get_end(self):
        return strfdate(timestamp_todate(self.time_end))

    def __unicode__(self):
        return u'%s active %s' % (self.name, self.is_active)


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

    is_hidden = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s' % self.ID


class Location(models.Model):
    class Meta:
        verbose_name = "Location"
        app_label = QRAAT_APP_LABEL
        db_table = "location"

    ID = models.AutoField(primary_key=True)  # int(11), auto_increment

    projectID = models.ForeignKey(Project, db_column="projectID")

    name = models.CharField(max_length=50)  # varchar(50)

    location = models.CharField(max_length=100)  # varchar(100)

    latitude = models.DecimalField(
        max_digits=10, decimal_places=6)  # decimal(10,6)

    longitude = models.DecimalField(
        max_digits=11, decimal_places=6)  # decimal(11,6)

    easting = models.DecimalField(
        default=0.00, max_digits=9, decimal_places=2)  # decimal(9,2) unsigned

    northing = models.DecimalField(
        default=0.00, max_digits=10,
        decimal_places=2)  # decimal(10,2) unsigned

    utm_zone_number = models.SmallIntegerField(
        max_length=3, default=10)  # tinyint(3) unsigned, default 10

    utm_zone_letter = models.CharField(
        default='S', max_length=1)  # char(1), default S

    elevation = models.DecimalField(
        default=0.00, max_digits=7,
        decimal_places=2)  # decimal(7,2), default 0.00

    is_hidden = models.BooleanField(default=False)

    def verbose_name(self):
        return self._meta.verbose_name

    def hide(self):
        objs_related = self.get_objs_related()

        for obj in objs_related:
            obj.hide()

        self.is_hidden = True
        self.save()

    def get_objs_related(self):
        objs_related = []
        return objs_related

    def __unicode__(self):
        return u'%s' % self.name


class Telemetry(models.Model):
    class Meta:
        verbose_name = "Telemetry"
        app_label = QRAAT_APP_LABEL
        db_table = "telemetry"

    ID = models.AutoField(primary_key=True)

    siteID = models.ForeignKey(Site, db_column="siteID")

    datetime = models.DateTimeField()

    timezone = models.CharField(max_length=6)

    intemp = models.DecimalField(max_digits=4, decimal_places=2)

    extemp = models.DecimalField(max_digits=4, decimal_places=2)

    voltage = models.DecimalField(max_digits=4, decimal_places=2)

    ping_power = models.IntegerField(max_length=11)

    ping_computer = models.IntegerField(max_length=11)

    site_status = models.IntegerField(max_length=11)

    timestamp = models.BigIntegerField(max_length=20)
