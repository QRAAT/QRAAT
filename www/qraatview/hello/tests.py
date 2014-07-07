from django.test import TestCase
from hello.models import tx_ID, TxInfo, TxType


class TransmitterTestCase(TestCase):
    def setUp(self):
        tx1_type = TxType.objects.create(
            RMG_type="pulse", tx_table_name="tx_pulse")
        tx1_info = TxInfo.objects.create(
            tx_type_ID=tx1_type.ID, manufacturer="Ben Kamen", 
            model="Tune-able Transmitter")
        tx1_ID = tx_ID.objects.create(tx_info=tx1_info.ID, active=0)

    def test_tx_ID_created(self):
        tx1 = tx_ID.objects.get(ID=tx1_ID.ID)
        self.assertEqual(tx1.tx_info_ID, tx1_ID.tx_info_ID)
        self.assertEqual(tx1.active, tx1_ID.active)

