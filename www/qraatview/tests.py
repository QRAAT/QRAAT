from django.test import TestCase
from models import Project, Target, Tx, TxMake

class ProjectTestCase(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(ownerID=1, is_public=0)

    def test_create_project(self):
        project1 = Project.objects.get(pk=self.project1.pk)
        self.assertEquals(project1, self.project1, msg="Projects are different")

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
        tx = Tx.objects.create(projectID=self.project,tx_makeID=tx_make)

        db_tx_make = TxMake.objects.get(pk=tx_make.pk)
        db_tx = Tx.objects.get(pk=tx.pk)

        self.assertEquals(db_tx_make, db_tx, msg="Tx make are different")
        self.assertEquals(tx, db_tx, msg="Tx are different")
