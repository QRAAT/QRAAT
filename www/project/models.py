# File: qraat_site models.py

from django.db import models
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from utils import timestamp_todate, strftime

QRAAT_APP_LABEL = 'project'
COLLABORATOR_PERMISSIONS = (
    ("can_change", "Users can change the project data"),
    ("can_hide", "Users can hide a project"))
VIEWER_PERMISSIONS = (
    ("can_view", "Users can view the project data"),)



class Project(models.Model):
    """**Project Model Object**.
    This is the Django's model representation for a project in QRAAT
    Database.

    :param ID: Project id
    :param ownerID: id of the user that owns the project
    :param name: Project's name
    :param is_public: Flag indicating public project. default: false
    :param is_hidden: Flag indicating hidden project. default: false"""

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
        """This method is called when the project is created.
        It adds djago's permissions to change the project for a given group.

        :param group:: Project's collaborators group in django's database
        :type group: Group.
        """

        [group.permissions.add(permission)
            for permission in map(
                lambda p: Permission.objects.get(codename=p[0]),
                              (self._collaborator_permissions
                                  + self._viewer_permissions))]

    def add_viewers_permissions(self, group):
        """This method is called when the project is created.
        It adds djago's permissions to visualize the
        project for a given group.

        :param group: Project's viewers group in django's database
        :type group: Group.
        """

        [group.permissions.add(permission)
            for permission in map(
                lambda p: Permission.objects.get(
                    codename=p[0]), self._viewer_permissions)]

    def get_locations(self):
        """Project locations getter"""

        return Location.objects.filter(
            projectID=self.ID).exclude(is_hidden=True)

    def get_deployments(self):
        """Project deployments getter"""

        return Deployment.objects.filter(
            projectID=self.ID).exclude(is_hidden=True).order_by('-is_active')

    def get_transmitters(self):
        """Project transmitters getter"""

        return Tx.objects.filter(projectID=self.ID).exclude(is_hidden=True)

    def get_targets(self):
        """Project targets getter"""

        return Target.objects.filter(projectID=self.ID).exclude(is_hidden=True)

    def create_viewers_group(self):
        """This method is called when the project is created.
        It creates a django's group and a row in qraat.auth_project_viewers.
        Together they will be the viewers group
        of the project"""

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
        """This method is called when the project is created.
        It creates a django's group and a row in qraat.auth_project_viewers.
        Together they will be the collaborators group
        of the project"""

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
        """ Group getter, encapsulates a query to
        groups objects to reuse code"""

        return Group.objects.get(id=group_id)

    def get_viewers_group(self):
        """Project viewers group getter

        **ObjectDoesNotExist**:
            Creates the group if for some reason group doesn't exist"""

        try:
            group_id = AuthProjectViewer.objects.get(projectID=self.ID).groupID
        except ObjectDoesNotExist:  # for some reason group wasn't created
            group_id = self.create_viewers_group().id

        return self.get_group(group_id)

    def get_collaborators_group(self):
        """Project collaborators group getter
        **ObjectDoesNotExist**:
            Creates the group if for some reason group doesn't exist"""

        try:
            group_id = AuthProjectCollaborator.objects.get(
                projectID=self.ID).groupID
        except ObjectDoesNotExist:
            group_id = self.create_collaborators_group().id

        return self.get_group(group_id)

    def is_owner(self, user):
        """Checks if given user is the owner of the project"""
        return user.id == self.ownerID

    def is_collaborator(self, user):
        """Checks if given user is collaborator on the project"""
        return user in self.get_collaborators_group().user_set.all()

    def is_viewer(self, user):
        """Checks if given user is viewer on the project"""
        return user in self.get_viewers_group().user_set.all()

    def set_permissions(self, group):
        """Method that encapsulates permission
        setter for viewers and collaborators"""

        if group == self.get_viewers_group():
            self.add_viewers_permissions(group)
        elif group == self.get_collaborators_group():
            self.add_collaborator_permissions(group)

    def __unicode__(self):
        return u'ID = %d name = %s' % (self.ID, self.name)


class AuthProjectViewer(models.Model):
    """**AuthProjectViewer Class**
    This is the Django's model representation for a auth_project_viewer
    object in QRAAT's Database

    :param ID: obj id
    :param projectID: id of the project that owns this obj
    :param groupID: django's group id that this obj is linked to"""

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
    """**AuthProjectCollaborator Class**
    This is the Django's model representation for a auth_project_collaborator
    object in QRAAT's Database

    :param ID: obj id
    :param projectID: id of the project that owns this obj
    :param groupID: django's group id that this obj is linked to"""

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
    """**Position Class**
    This is the Django's model representation for a position
    object in QRAAT's Database

    :param ID: obj id
    :param projectID: id of the project that owns this obj
    :param deploymentID: deployment's id that this obj is linked to
    :param timestamp: UTC timestamp
    :param latitute:
    :param longitude:
    :param easting: (UTM north)
    :param northing: (UTM zone)
    :param utm_zone_number: (UTM zone)
    :param utm_zone_letter: (UTM zone letter)
    :param likelihood: Maximum likelihood value over search space
    :param activity: Averaged over bearing data from all sites"""

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
    """**Tx Model Object**.
    This is the Django's model representation for a transmitter in QRAAT's
    Database.

    :param ID: Tx id
    :param name: Transmitter's name
    :param serial_no: Transmitter's serial number
    :param tx_makeID: Foreign key for tx_make table
    :param projectID: Foreign key for project that owns this transmitter
    :param frequency: Transmitter's frequency
    :param is_hidden: Transmitter's deletion status"""

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
        """Models verbose name getter

        :returns: str -- Model's verbose name"""

        return self._meta.verbose_name

    def hide(self):
        """This method hides a transmitter and it's
        related objects recursively"""

        objs_related = self.get_objs_related()

        for obj in objs_related:
            obj.hide()

        self.is_hidden = True
        self.save()

    def get_objs_related(self):
        """This method is for intern use. It returns objects that have
        this transmitter as foreign key

        :returns:  list -- List of model objects"""

        objs_related = Deployment.objects.exclude(
            is_hidden=True).filter(txID=self)
        return objs_related

    def __unicode__(self):
        return u'%s %s' % (self.name, self.serial_no)


class TxParameters(models.Model):
    """**Tx Parameters Model Object**.
    This is the Django's model representation for a tx_parameters in QRAAT's
    Database.

    :param ID: ID
    :param txID: Foreign key for transmitter
    :param name: parameter's name
    :param value: parameter's value
    :param units: parameter's units"""

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
    """**Tx Make Parameters Model Object**.
    This is the Django's model representation for a
    tx_make_parameters in QRAAT's Database.

    :param ID: ID
    :param tx_makeID: Foreign key for tx_make
    :param name: parameter's name
    :param value: parameter's value
    :param units: parameter's units"""

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
    """**Target Model Object**.
    This is the Django's model representation for a target in QRAAT's
    Database.

    :param ID: ID
    :param name: Target's name
    :param description: target's description
    :param max_speed_family: Type of max speed function: exp, linear, or cons.
    :param projectID: Foreign key for project
    :param is_hidden: target's deletion status"""

    class Meta:
        verbose_name = "Target"
        app_label = QRAAT_APP_LABEL
        db_table = "target"

    ID = models.AutoField(
        primary_key=True)  # primary_key auto-increment int(10)

    name = models.CharField(max_length=50)

    description = models.TextField()  # text

    max_speed_family = models.CharField(max_length=16,
                                        choices=(('exp', 'Exponential'),
                                                 ('linear', 'Piecewise linear'),
                                                 ('const', 'Constant')))

    speed_burst     = models.FloatField()
    speed_sustained = models.FloatField()
    speed_limit     = models.FloatField()

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
    """**Deployment Model Object**.
    This is the Django's model representation for a deployment in QRAAT's
    Database.

    :param ID: ID
    :param name: deployment's name
    :param description: deployment's description
    :param time_start: date that deployment has started (timestamp)
    :param time_end: date that deployment has ended (timestamp)
    :param txID: Foreign key for transmitter
    :param targetID: Foreign key for target
    :param projectID: Foreign key for project
    :param is_active: deployment's status
    :param is_hidden: deployment's deletion status"""

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
        if(self.time_start != None):
            return strftime(timestamp_todate(self.time_start))
        else:
            return ""

    def get_end(self):
        if(self.time_end != None):
            return strftime(timestamp_todate(self.time_end))
        else:
            return ""

    def __unicode__(self):
        return u'%s active %s' % (self.name, self.is_active)


class Location(models.Model):
    """**Location Model Object**.
    This is the Django's model representation for a location in QRAAT's
    Database.

    :param ID: ID
    :param name: location's name
    :param projectID: Foreign key for project
    :param is_hidden: locations's deletion status"""

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

    timestamp = models.DecimalField(max_digits=16, decimal_places=6)


class Est(models.Model):
    class Meta:
        verbose_name = "Est"
        app_label = QRAAT_APP_LABEL
        db_table = "est"

    ID = models.AutoField(primary_key=True)

    siteID = models.ForeignKey(Site, db_column="siteID")

    timestamp = models.DecimalField(max_digits=16, decimal_places=6)

    frequency = models.IntegerField(max_length=11)

    center = models.IntegerField(max_length=11)

    fdsp = models.FloatField()

    fd1r = models.FloatField()
    fd1i = models.FloatField()
    fd2r = models.FloatField()
    fd2i = models.FloatField()
    fd3r = models.FloatField()
    fd3i = models.FloatField()
    fd4r = models.FloatField()
    fd4i = models.FloatField()

    band3 = models.SmallIntegerField(max_length=6)

    band10 = models.SmallIntegerField(max_length=6)

    edsp = models.FloatField()

    ed1r = models.FloatField()
    ed1i = models.FloatField()
    ed2r = models.FloatField()
    ed2i = models.FloatField()
    ed3r = models.FloatField()
    ed3i = models.FloatField()
    ed4r = models.FloatField()
    ed4i = models.FloatField()

    ec = models.FloatField()

    tnp = models.FloatField()

    nc11r = models.FloatField()
    nc11i = models.FloatField()
    nc12r = models.FloatField()
    nc12i = models.FloatField()
    nc13r = models.FloatField()
    nc13i = models.FloatField()
    nc14r = models.FloatField()
    nc14r = models.FloatField()
    nc21r = models.FloatField()
    nc21i = models.FloatField()
    nc22r = models.FloatField()
    nc22i = models.FloatField()
    nc23r = models.FloatField()
    nc23i = models.FloatField()
    nc24r = models.FloatField()
    nc24i = models.FloatField()
    nc31r = models.FloatField()
    nc31i = models.FloatField()
    nc32r = models.FloatField()
    nc32i = models.FloatField()
    nc33r = models.FloatField()
    nc33i = models.FloatField()
    nc34r = models.FloatField()
    nc34i = models.FloatField()
    nc41r = models.FloatField()
    nc41i = models.FloatField()
    nc42r = models.FloatField()
    nc42i = models.FloatField()
    nc43r = models.FloatField()
    nc43i = models.FloatField()
    nc44r = models.FloatField()
    nc44i = models.FloatField()

    fdsnr = models.FloatField()

    edsnr = models.FloatField()

    deploymentID = models.ForeignKey(Deployment, db_column="deploymentID")


