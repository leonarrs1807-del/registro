"""Old inactive periods must be readable before the user decides to edit them."""
from contextlib import closing
from pathlib import Path
import sqlite3,unittest
import app_storage,db,periodos
from tests import test_instrumentos as fixtures


def legacy_period(source,target,course,session):
    app_storage.copy_database(source,target)
    with closing(sqlite3.connect(target)) as conn,conn:
        conn.execute('DROP TABLE Unidades_Didacticas')
        conn.execute('''CREATE TABLE Unidades_Didacticas(id INTEGER PRIMARY KEY,
            curso_id INTEGER NOT NULL,grado TEXT NOT NULL,seccion TEXT NOT NULL,
            nombre TEXT NOT NULL,proposito TEXT DEFAULT '',inicio TEXT DEFAULT '',fin TEXT DEFAULT '')''')
        conn.execute("INSERT INTO Unidades_Didacticas VALUES(88,?,'3°','A','Unidad antigua','','','')",(course,))
        conn.execute('UPDATE Sesiones_Clase SET unidad_id=88 WHERE id=?',(session,))
    periodos.identify(target,2034,1,'Trimestres')
    return target


class LegacyPeriodTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session

    def old(self):
        db.guardar_notas_globales_sesion(self.session,{self.student:12.5},self.path)
        return legacy_period(self.path,Path(self.temp.name)/'periodo-antiguo.db',self.course,self.session)

    def test_catalog_lists_one_document_when_root_and_active_path_are_aliases(self):
        alias=self.path.parent/'..'/self.path.parent.name
        before=self.path.read_bytes();rows=periodos.catalog(alias,self.path.resolve())
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['path'].resolve(),self.path.resolve())
        self.assertEqual(self.path.read_bytes(),before)

    def test_reading_inactive_legacy_period_does_not_modify_or_upgrade_it(self):
        path=self.old();before=path.read_bytes();rows=periodos.units(path)
        self.assertEqual([(u['id'],u['nombre']) for u in rows],[(88,'Unidad antigua')])
        self.assertEqual(before,path.read_bytes())
        with closing(sqlite3.connect(path)) as conn:self.assertNotIn('general',{r[1] for r in conn.execute('PRAGMA table_info(Unidades_Didacticas)')})

    def test_first_explicit_edit_upgrades_old_period_and_keeps_notes(self):
        path=self.old()
        periodos.save_unit(path,None,None,None,'Unidad actualizada',identity=88)
        with closing(sqlite3.connect(path)) as conn:
            self.assertIn('general',{r[1] for r in conn.execute('PRAGMA table_info(Unidades_Didacticas)')})
            self.assertEqual(conn.execute('SELECT unidad_id FROM Sesiones_Clase WHERE id=?',(self.session,)).fetchone()[0],88)
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(self.session,)).fetchone()[0],12.5)
        self.assertTrue(list((path.parent/'backups').glob(path.stem+'-*-antes-_upgrade_units.db')))

    def test_closed_legacy_and_pre_unit_records_can_be_read_without_changes(self):
        path=self.old()
        with closing(sqlite3.connect(path)) as conn,conn:
            conn.execute('CREATE TABLE IF NOT EXISTS Estado_Periodo(id INTEGER PRIMARY KEY,cerrado INTEGER)');conn.execute('INSERT OR REPLACE INTO Estado_Periodo VALUES(1,1)')
        before=path.read_bytes();self.assertEqual(len(periodos.units(path)),1);self.assertEqual(before,path.read_bytes())
        with closing(sqlite3.connect(path)) as conn,conn:
            conn.execute('UPDATE Sesiones_Clase SET unidad_id=NULL');conn.execute('DROP TABLE Unidades_Didacticas')
        before=path.read_bytes();self.assertEqual(periodos.units(path),[]);self.assertEqual(before,path.read_bytes())
