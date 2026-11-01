from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import json
import sqlite3
import tempfile
import unittest
import sys
import uuid
from unittest.mock import patch
from licencias import OfflineLicensing, course_key
from licencias_emisor import create_keys, sign_request
import db
from db_safety import connection, set_license_policy


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        self.public = create_keys(self.folder/'privada.pem', self.folder/'publica.pem', 'ClaveVendedorPrueba123')
        self.private = (self.folder/'privada.pem').read_bytes()
        self.course = 'secundaria:matematica'
        self.other = 'primaria:matematica'
        self.service = self.make_service(self.folder/'cliente')
        self.service.register('Docente Prueba', 'docente@example.com', 'ana', 'ClaveCliente123', self.course)
        self.catalog = [dict(key=self.course,label='Secundaria · Matemática'), dict(key=self.other,label='Primaria · Matemática')]

    def make_service(self, folder, device='a'*64, public=None):
        return OfflineLicensing(folder, self.public if public is None else public,
            device=device, clock=lambda:self.now, registry=False)

    def issue(self, courses=None, expires=None):
        return sign_request(self.service.request(self.catalog), self.private, 'ClaveVendedorPrueba123',
            courses or [self.course], expires=expires, now=self.now)

    def test_thirty_day_demo_only_one_course_and_password_auth(self):
        self.assertTrue(self.service.authenticate('ANA', 'ClaveCliente123'))
        self.assertFalse(self.service.authenticate('ana', 'incorrecta'))
        self.assertTrue(self.service.can_edit(self.course))
        self.assertFalse(self.service.can_edit(self.other))
        self.assertEqual(self.service.status()['days'], 30)
        self.now += timedelta(days=29,hours=23)
        self.assertEqual(self.service.status()['days'], 1)
        self.now += timedelta(hours=1)
        self.assertFalse(self.service.can_edit(self.course))
        self.assertEqual(self.service.status()['mode'], 'vencida')

    def test_restart_does_not_restart_demo_or_change_trial_course(self):
        self.now += timedelta(days=31)
        other = self.make_service(self.folder/'cliente')
        self.assertEqual(other.status()['mode'], 'vencida')
        with self.assertRaises(ValueError):other.register('Nuevo', 'nuevo@example.com', 'n', 'OtraClave123', self.other)

    def test_request_contains_no_password_or_student_data(self):
        request = self.service.request(self.catalog)
        self.assertNotIn('password', request)
        self.assertNotIn('ClaveCliente123', json.dumps(request))
        raw = self.service.path.read_bytes()
        self.assertNotIn(b'ClaveCliente123', raw)
        self.assertNotIn(b'docente@example.com', raw)

    def test_courses_can_be_bought_in_packages_after_demo(self):
        license1 = self.issue()
        self.now += timedelta(days=40)
        self.service.import_license(license1)
        self.assertTrue(self.service.can_edit(self.course))
        self.assertFalse(self.service.can_edit(self.other))
        self.service.import_license(self.issue([self.other]))
        self.assertTrue(self.service.can_edit(self.other))
        self.assertTrue(self.make_service(self.folder/'cliente').can_edit(self.course))

    def test_complete_package_unlocks_future_courses(self):
        self.service.import_license(self.issue(['*']))
        self.now += timedelta(days=1000)
        self.assertTrue(self.service.can_edit('secundaria:otra-area'))

    def test_custom_three_course_package_enables_exactly_that_selection(self):
        keys=[self.course,self.other,'secundaria:comunicacion','primaria:personal-social','secundaria:ingles']
        catalog=[dict(key=key,label=key) for key in keys]
        chosen=[self.other,'secundaria:comunicacion','secundaria:ingles']
        document=sign_request(self.service.request(catalog),self.private,'ClaveVendedorPrueba123',chosen,now=self.now)
        self.service.import_license(document);self.now+=timedelta(days=40)
        self.assertEqual([key for key in keys if self.service.can_edit(key)],[key for key in keys if key in chosen])

    def test_license_for_another_computer_or_account_is_rejected(self):
        license1 = self.issue()
        for name, device in [('otro-equipo','b'*64),('otra-cuenta','a'*64)]:
            with self.subTest(name=name):
                service = self.make_service(self.folder/name, device)
                service.register('Otra', 'docente@example.com', 'ana', 'ClaveCliente123', self.course)
                with self.assertRaisesRegex(ValueError, 'otra cuenta o computadora'):service.import_license(license1)

    def test_tampered_license_cannot_unlock_all_courses(self):
        document = self.issue()
        forged = copy.deepcopy(document)
        forged['payload']['courses'] = ['*']
        with self.assertRaises(ValueError):self.service.import_license(forged)
        self.assertFalse(self.service.can_edit(self.other))

    def test_missing_or_wrong_issuer_key_cannot_disable_activation(self):
        document = self.issue()
        self.service.public_key = b''
        with self.assertRaisesRegex(ValueError, 'clave pública'):self.service.import_license(document)
        self.now += timedelta(days=31)
        self.assertFalse(self.service.can_edit(self.course))
        wrong = create_keys(self.folder/'otra_priv.pem', self.folder/'otra_pub.pem', 'ContraseñaPrueba123')
        self.service.public_key = wrong
        with self.assertRaises(ValueError):self.service.import_license(document)

    def test_clock_rollback_blocks_edits_without_deleting_data(self):
        self.now += timedelta(days=20); self.service.status()
        self.now -= timedelta(days=10)
        self.assertEqual(self.service.status()['mode'], 'reloj')
        self.assertFalse(self.service.can_edit(self.course))
        self.now += timedelta(days=10)
        self.assertTrue(self.service.can_edit(self.course))

    def test_damaged_account_or_copied_state_does_not_reset_demo(self):
        self.service.path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'No se reinicia la demo'):self.make_service(self.folder/'cliente')

    def test_expiring_license_keeps_other_packages(self):
        self.service.import_license(self.issue([self.other], expires='2026-11-02'))
        self.service.import_license(self.issue([self.course]))
        self.now += timedelta(days=35)
        self.assertTrue(self.service.can_edit(self.course))
        self.assertFalse(self.service.can_edit(self.other))

    def test_profile_change_preserves_license_identity(self):
        document = self.issue()
        self.service.update_profile('Nuevo nombre', 'nuevo', 'NuevaClave123')
        self.service.import_license(document)
        self.assertTrue(self.service.authenticate('nuevo','NuevaClave123'))
        self.assertEqual(self.service.state['email'], 'docente@example.com')

    def test_key_generation_never_overwrites_existing_keys(self):
        before = self.private
        with self.assertRaises(ValueError):create_keys(self.folder/'privada.pem',self.folder/'publica.pem','OtraContraseña123')
        self.assertEqual((self.folder/'privada.pem').read_bytes(),before)
        with self.assertRaises(ValueError):sign_request(self.service.request(self.catalog),self.private,'incorrecta',[self.course],now=self.now)

    def test_course_identity_is_stable_across_documents_and_accents(self):
        self.assertEqual(course_key('Matemática (Primaria)','Primaria'), self.other)
        self.assertEqual(course_key('MATEMATICA','Secundaria'), self.course)

    @unittest.skipUnless(sys.platform=='win32','Protección DPAPI y registro de Windows')
    def test_reinstall_keeps_expired_trial_in_windows_user_registry(self):
        import winreg
        path=rf'Software\RegistroDocente\Pruebas\{uuid.uuid4()}'
        try:
            with patch('licencias.REGISTRY_PATH',path):
                folder=self.folder/'reinstalacion'
                service=OfflineLicensing(folder,self.public,device='c'*64,clock=lambda:self.now,registry=True)
                service.register('Ana','ana@example.com','ana','PruebaTemporal123',self.course)
                self.now+=timedelta(days=31)
                self.assertEqual(service.status()['mode'],'vencida')
                service.path.unlink()
                restored=OfflineLicensing(folder,self.public,device='c'*64,clock=lambda:self.now,registry=True)
                self.assertEqual(restored.status()['mode'],'vencida')
                self.assertEqual(restored.state['account_id'],service.state['account_id'])
        finally:
            try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path)
            except FileNotFoundError:pass


class LicenseDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(set_license_policy)
        self.folder = Path(self.temp.name)
        self.path = self.folder/'notas.db'
        db.inicializar_db(self.path)
        self.courses = db.obtener_cursos(db_path=self.path)
        self.course, name, _ = self.courses[0]
        self.comp = db.obtener_competencias_por_curso(self.course,self.path)[0][0]
        self.cap = db.obtener_capacidades_por_competencia(self.comp,self.path)[0][0]
        self.student = db.agregar_estudiante('Ana','Licencia',db_path=self.path)
        self.now = datetime.now(timezone.utc)
        self.service = OfflineLicensing(self.folder/'cuenta', device='a'*64,clock=lambda:self.now,registry=False)
        self.service.register('Ana','ana@example.com','ana','ClavePrueba123',course_key(name,'Secundaria'))
        set_license_policy(self.service,required=True)

    def test_sql_guard_blocks_unpurchased_course_and_keeps_authorized_edits(self):
        db.guardar_nota_manual_capacidad(self.student,self.cap,15,self.path)
        other_course = self.courses[1][0]
        comp = db.obtener_competencias_por_curso(other_course,self.path)[0][0]
        cap = db.obtener_capacidades_por_competencia(comp,self.path)[0][0]
        with self.assertRaises(sqlite3.IntegrityError):db.guardar_nota_manual_capacidad(self.student,cap,20,self.path)
        with connection(self.path) as conn:
            self.assertEqual(conn.execute('SELECT nota_manual FROM Notas_Manuales_Capacidad').fetchall(),[(15,)])
            self.assertFalse(conn.execute("SELECT 1 FROM sqlite_master WHERE name LIKE 'licencia_%'").fetchone())

    def test_expired_demo_blocks_writes_and_allows_reading_and_export(self):
        db.guardar_nota_manual_capacidad(self.student,self.cap,15,self.path)
        self.now += timedelta(days=31)
        with self.assertRaises(sqlite3.IntegrityError):db.guardar_nota_manual_capacidad(self.student,self.cap,20,self.path)
        _, rows = db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',self.path)
        self.assertEqual(len(rows),1)
        import documento
        documento.save_document(self.folder/'conservado.registro',self.path)
        self.assertTrue((self.folder/'conservado.registro').exists())

    def test_cascade_delete_of_licensed_course_still_works(self):
        sid = db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Tema','',1,[(self.cap,'Criterio')],db_path=self.path)
        db.guardar_calificaciones_y_asistencia_sesion(sid,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:12})],db_path=self.path)
        db.eliminar_sesion_clase(sid,self.path)
        with connection(self.path) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Notas_Sesion_Capacidad').fetchone()[0],0)
