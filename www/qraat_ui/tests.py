from django.test import TestCase
from qraat_ui.models import tx_ID, TxInfo, TxType


class TransmitterTestCase(TestCase):

    def setUp(self):
        self.tx1_type = TxType.objects.create(
            RMG_type="pulse", tx_table_name="tx_pulse")
        self.tx1_info = TxInfo.objects.create(
            tx_type_ID=self.tx1_type, manufacturer="Ben Kamen",
            model="Tune-able Transmitter")
        self.tx1_ID = tx_ID.objects.create(tx_info_ID=self.tx1_info, active=0)

    def test_tx_ID_created(self):
        tx1 = tx_ID.objects.get(ID=self.tx1_ID.ID)
        self.assertEqual(tx1.tx_info_ID, self.tx1_ID.tx_info_ID)
        self.assertEqual(tx1.active, self.tx1_ID.active)
