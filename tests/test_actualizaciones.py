"""Untrusted updates cannot execute; upgrading preserves grades, models and activation."""
from contextlib import closing
from pathlib import Path
import hashlib,io,json,sqlite3,tempfile,unittest
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
import actualizaciones as updates
from tests import test_instrumentos as fixtures


class UpdateTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session

    def manifest(self):
        self.key=Ed25519PrivateKey.generate();self.public=self.key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)
        self.binary=b'installer fixture'
        return dict(schema=1,app_id='registro',edicion='comercial',plataforma='windows-x64',version='2.4.0',
            url='https://example.com/RegistroDocente-Setup.exe',sha256=hashlib.sha256(self.binary).hexdigest(),bytes=len(self.binary),notas='Mejoras')

    def test_signed_manifest_accepts_only_newer_trusted_commercial_versions(self):
        manifest=self.manifest();document=updates.sign_manifest(manifest,self.key)
        self.assertEqual(updates.verify_manifest(document,self.public,'2.3.0'),manifest)
        self.assertIsNone(updates.verify_manifest(document,self.public,'2.4.0'))
        self.assertIsNone(updates.verify_manifest(document,self.public,'2.5.0'))
        document['payload']['url']='https://evil.example/fake.exe'
        with self.assertRaises(ValueError):updates.verify_manifest(document,self.public,'2.3.0')
        for field,value in [('edicion','personal'),('app_id','otra'),('url','http://insecure.example/a'),('bytes',-1)]:
            wrong={**manifest,field:value}
            with self.assertRaises(ValueError):updates.validate_manifest(wrong)

    def test_download_checks_actual_size_and_hash_and_removes_partial_files(self):
        manifest=self.manifest()
        with patch('actualizaciones.open_https',return_value=io.BytesIO(self.binary)):
            file=updates.download_installer(manifest,self.temp.name);self.assertEqual(file.read_bytes(),self.binary)
        for content in (b'truncated',self.binary+b'oversize',b'X'*len(self.binary)):
            with patch('actualizaciones.open_https',return_value=io.BytesIO(content)),self.assertRaises(ValueError):updates.download_installer(manifest,self.temp.name)
        self.assertFalse(list((Path(self.temp.name)/'updates').rglob('*.part')))

    def test_snapshot_preserves_notes_library_settings_and_license_without_touching_originals(self):
        import db
        root=Path(self.temp.name);db.guardar_notas_globales_sesion(self.session,{self.student:12.5},self.path)
        library=root/'biblioteca'/'instrumentos.db';library.parent.mkdir()
        with closing(sqlite3.connect(library)) as conn,conn:conn.execute('CREATE TABLE modelos(nombre TEXT)');conn.execute("INSERT INTO modelos VALUES('Mi rúbrica')")
        (root/'cuenta.activacion').write_bytes(b'protected-account');(root/'settings.json').write_text('{"active_database":"datos.db"}')
        before=self.path.read_bytes();folder=updates.backup_before_update(root,self.path,'2.4.0')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual((folder/'cuenta.activacion').read_bytes(),b'protected-account')
        self.assertEqual((folder/'settings.json').read_bytes(),(root/'settings.json').read_bytes())
        with closing(sqlite3.connect(folder/'datos.db')) as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],12.5)
        with closing(sqlite3.connect(folder/'biblioteca'/'instrumentos.db')) as conn:self.assertEqual(conn.execute('SELECT nombre FROM modelos').fetchone()[0],'Mi rúbrica')

    def test_installer_cannot_start_with_changed_download(self):
        manifest=self.manifest();path=Path(self.temp.name)/'setup.exe';path.write_bytes(self.binary)
        with patch('actualizaciones.sys.platform','win32'),patch('actualizaciones.subprocess.Popen') as launch:
            updates.launch_installer(path,manifest);self.assertIn('/REINICIAR=1',launch.call_args.args[0])
            path.write_bytes(b'tampered')
            with self.assertRaises(ValueError):updates.launch_installer(path,manifest)
            self.assertEqual(launch.call_count,1)
