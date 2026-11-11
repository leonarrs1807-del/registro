"""Update checks stay responsive and installing never discards pending teacher data."""
import os,threading,unittest
from unittest.mock import patch
import db
from tests import test_gui as fixtures


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere pantalla o Xvfb')
class UpdateInterfaceTests(unittest.TestCase):
    setUp=fixtures.DesktopTests.setUp

    def test_update_requires_saved_forms_and_saves_grades_before_restart(self):
        self.app._formularios_pendientes.add('Institución')
        with patch('tkinter.messagebox.showinfo'):
            self.assertFalse(self.app.preparar_guardado_actualizacion())
        self.assertEqual(self.app._formularios_pendientes,{'Institución'});self.app._formularios_pendientes.clear()
        self.app.edicion_desbloqueada=True;tree=self.app.planilla_nativa;iid=tree.get_children()[0]
        row=list(tree.item(iid,'values'));row[4]='12.5';tree.item(iid,values=row);self.app.marcar_planilla_pendiente()
        with patch('tkinter.messagebox.askyesno',return_value=False):self.assertFalse(self.app.preparar_guardado_actualizacion())
        self.assertTrue(self.app._planilla_pendiente)
        with patch('tkinter.messagebox.askyesno',return_value=True),patch('tkinter.messagebox.showinfo'):
            self.assertTrue(self.app.preparar_guardado_actualizacion())
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],12.5)
        self.assertFalse(self.errors)

    def test_background_update_check_keeps_window_responsive(self):
        release=threading.Event();observed=[];identity=self.app.winfo_id()
        def checking(*args):release.wait(2);return {'version':'2.4.0'}
        def tick():observed.append('responsive');release.set()
        with patch.object(self.app,'update_url',return_value='https://example.com/actualizaciones/registro'),patch('actualizaciones_ui.check_update',side_effect=checking),patch('actualizaciones_ui.UpdateDialog') as dialog:
            self.app.buscar_actualizaciones();self.app.after(50,tick);self.app.after(400,self.app.quit);self.app.mainloop()
            self.assertEqual(observed,['responsive']);dialog.assert_called_once()
        self.assertEqual(self.app.winfo_id(),identity);self.assertFalse(self.errors)
