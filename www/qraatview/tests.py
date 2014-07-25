from django.test import TestCase
from models import Project, Target

"""
class TransmitterTestCase(TestCase):

    def setUp(self):
        self.tx1_type = TxType.objects.create(
            RMG_type="pulse", tx_table_name="tx_pulse")
        self.tx1_info = TxInfo.objects.create(
            tx_type_ID=self.tx1_type, manufacturer="Ben Kamen",
            model="Tune-able Transmitter")
        self.tx1_ID = tx_ID.objects.create(tx_info_ID=self.tx1_info, active=0)


    def test_TxInfoCreated(self):
        tx_info = TxInfo.objects.get(ID=self.tx1_info.ID)
        self.assertEqual(tx_info.ID, self.tx1_info.ID)
        self.assertEqual(tx_info.model, self.tx1_info.model)
        self.assertEqual(tx_info.manufacturer, self.tx1_info.manufacturer)

    def test_tx_ID_created(self):
        tx1 = tx_ID.objects.get(ID=self.tx1_ID.ID)
        self.assertEqual(tx1.tx_info_ID, self.tx1_ID.tx_info_ID)
        self.assertEqual(tx1.active, self.tx1_ID.active)
"""

class ProjectTestCase(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(ownerID=1, is_public=0)

    def test_create_project(self):
        project1 = Project.objects.all()[0]
        self.assertEqual(project1.ID, self.project1.ID)
        self.assertEqual(project1.is_public=self.project1.is_public)

    def test_project_public(self):
        project = Project.objects.create(ownerID=1, is_public=1)
        assertEqual(1, project.is_public)



