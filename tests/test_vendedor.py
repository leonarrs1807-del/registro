"""Seller choices must never carry over into the next buyer's license."""
import os
from pathlib import Path
import tempfile
import unittest
from licencias import OfflineLicensing


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere pantalla o Xvfb')
class SellerTests(unittest.TestCase):
    def test_opening_another_request_clears_all_previous_sale_permissions(self):
        from vendedor import SellerApp
        app=SellerApp();self.addCleanup(app.destroy)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        service=OfflineLicensing(Path(temp.name),device='a'*64,registry=False)
        service.register('Comprador','comprador@example.com','comprador','ClaveCliente123','secundaria:matematica')
        catalog=[dict(key='secundaria:matematica',label='Secundaria · Matemática'),
                 dict(key='primaria:matematica',label='Primaria · Matemática')]
        app.load_request(service.request(catalog))
        app.all_courses.set(True)
        for key,var in app.course_vars:var.set(True)
        app.expiry.insert(0,'2027-12-31');app.reference.insert(0,'Venta anterior')
        app.load_request(service.request(catalog))
        self.assertFalse(app.all_courses.get())
        self.assertFalse(any(var.get() for key,var in app.course_vars))
        self.assertEqual(app.expiry.get(),'');self.assertEqual(app.reference.get(),'')
        self.assertIn('0 curso',app.selection.cget('text'))
