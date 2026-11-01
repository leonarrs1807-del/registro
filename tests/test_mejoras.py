from contextlib import closing
from pathlib import Path
import csv,json,sqlite3,tempfile,unittest,zipfile
from PIL import Image
import openpyxl
import db,documento,reportes,app_storage
from graficos import category_figure,frequency_figure


class Improvements(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'registro.db'
        db.inicializar_db(self.path)
        self.course=db.obtener_cursos(db_path=self.path)[0][0]
        self.comp=db.obtener_competencias_por_curso(self.course,self.path)[0][0]
        self.cap=db.obtener_capacidades_por_competencia(self.comp,self.path)[0][0]
        self.e=db.agregar_estudiante('María','Muñoz','3°','A',db_path=self.path)
        self.s=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Sesión','',1,[(self.cap,'Criterio completo')],db_path=self.path)
        db.guardar_calificaciones_y_asistencia_sesion(self.s,[dict(estudiante_id=self.e,notas_por_capacidad={self.cap:13.2})],db_path=self.path)

    def test_empty_database_first_start(self):
        path=Path(self.temp.name)/'vacia.db'
        with closing(sqlite3.connect(path)):pass
        app_storage.prepare_storage(path);db.inicializar_db(path);app_storage.validate_database(path)
        self.assertTrue(list((path.parent/'backups').glob('vacia-*')))

    def test_legacy_schema_migrates_and_preserves_grades(self):
        with closing(sqlite3.connect(self.path)) as conn,conn:
            conn.execute('DROP TABLE Docente_Config')
        app_storage.prepare_storage(self.path);db.inicializar_db(self.path)
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],13.2)

    def test_unknown_database_remains_untouched(self):
        path=Path(self.temp.name)/'otra.db'
        with closing(sqlite3.connect(path)) as conn,conn:conn.execute('CREATE TABLE algo(id INTEGER)')
        original=path.read_bytes()
        with self.assertRaises(ValueError):app_storage.prepare_storage(path)
        self.assertEqual(original,path.read_bytes())

    def test_logo_native_document_roundtrip_all_records(self):
        image=Path(self.temp.name)/'logo.png';Image.new('RGB',(180,80),'blue').save(image)
        reportes.save_logo(image,self.path)
        doc=Path(self.temp.name)/'notas.registro';documento.save_document(doc,self.path)
        restored=Path(self.temp.name)/'abierto.db';documento.open_document(doc,restored)
        self.assertEqual(reportes.logo_bytes(self.path),reportes.logo_bytes(restored))
        with closing(sqlite3.connect(self.path)) as src,closing(sqlite3.connect(restored)) as dst:
            for table in ['Estudiantes','Sesiones_Clase','Notas_Sesion_Capacidad','Historial_Notas','Sesion_Capacidades']:
                self.assertEqual(src.execute(f'SELECT * FROM {table}').fetchall(),dst.execute(f'SELECT * FROM {table}').fetchall())
        with self.assertRaises(ValueError):documento.open_document(doc,restored)

    def test_internal_document_rejects_tampering(self):
        file=Path(self.temp.name)/'mal.registro'
        with zipfile.ZipFile(file,'w') as z:
            z.writestr('manifest.json',json.dumps({'format':'registro-docente','version':1,'sha256':'incorrecto'}));z.writestr('registro.db',b'x')
        target=Path(self.temp.name)/'no.db'
        with self.assertRaises(ValueError):documento.open_document(file,target)
        self.assertFalse(target.exists())

    def test_exports_full_names_numeric_grades_and_zero(self):
        for suffix in ['xlsx','csv','json']:
            file=Path(self.temp.name)/('notas.'+suffix)
            self.assertEqual(reportes.export_grades(file,self.path,self.course,'3°','A'),1)
            if suffix=='xlsx':
                wb=openpyxl.load_workbook(file);ws=wb['Calificativos']
                self.assertEqual(ws.cell(2,16).value,13.2);self.assertIn('Muñoz',[c.value for c in ws[2]])
                self.assertEqual(ws.freeze_panes,'G2');self.assertEqual(ws.cell(2,1).value,self.e);wb.close()
            elif suffix=='csv':
                with file.open(encoding='utf-8-sig',newline='') as stream:row=list(csv.DictReader(stream))[0]
                self.assertEqual(row['nota'],'13.2');self.assertEqual(row['apellidos'],'Muñoz')
                self.assertEqual(row['capacidad'],db.obtener_capacidades_por_competencia(self.comp,self.path)[0][1])

    def test_branding_does_not_move_template_headers(self):
        file=Path(self.temp.name)/'plantilla.xlsx';db.generar_plantilla_excel_estudiantes(file)
        image=Path(self.temp.name)/'logo.png';Image.new('RGB',(50,50),'red').save(image)
        reportes.save_logo(image,self.path);reportes.decorate_workbook(file,reportes.logo_bytes(self.path))
        wb=openpyxl.load_workbook(file);self.assertIn('Apellidos',[c.value.strip() if isinstance(c.value,str) else c.value for c in wb.active[1]])
        self.assertEqual(len(wb.active._images),1);wb.close()

    def test_percentages_are_values_not_duplicate_normalized_labels(self):
        fig=category_figure({'Clases':40,'Exámenes':25,'Trabajos':20,'Otros':15})
        self.assertEqual([p.get_width() for p in fig.axes[0].patches],[40,25,20,15])
        self.assertEqual([t.get_text() for t in fig.axes[0].texts],['40 %','25 %','20 %','15 %'])

    def test_frequency_chart_keeps_every_full_label(self):
        items=[(f'Capacidad número {i}: descripción completa para no ocultar información',i%3) for i in range(30)]
        fig=frequency_figure(items,'Capacidades')
        self.assertEqual(len(fig.axes[0].patches),30)
        self.assertGreater(fig.get_figheight(),15)
        self.assertIn('información',fig.axes[0].get_yticklabels()[0].get_text())

    def test_primary_sixth_grade_and_secondary_notes_stay_separate(self):
        with db.obtener_conexion(self.path) as conn:conn.execute("UPDATE Docente_Config SET nivel_educativo='Primaria' WHERE id=1")
        self.assertIn('6°',db.obtener_grados_y_secciones(self.path)[0])
        self.assertFalse(db.obtener_estudiantes_filtrados('3°','A',db_path=self.path))
        primary=db.agregar_estudiante('Niña','Primaria','3°','A',db_path=self.path)
        rows=db.obtener_estudiantes_filtrados('3°','A',db_path=self.path)
        self.assertEqual([r['ID'] for r in rows],[primary]);self.assertTrue(rows[0]['Codigo_Unico'].startswith('P'))
        self.assertTrue(all('Primaria' in name for _,name,_ in db.obtener_cursos(db_path=self.path)))
        with db.obtener_conexion(self.path) as conn:conn.execute("UPDATE Docente_Config SET nivel_educativo='Secundaria' WHERE id=1")
        self.assertEqual(db.obtener_estudiantes_filtrados('3°','A',db_path=self.path)[0]['ID'],self.e)
        self.assertEqual(reportes.grade_rows(self.path,self.course,'3°','A')[0]['nota'],13.2)

    def test_sheets_export_can_be_reimported_by_id_without_moving_grades(self):
        file=Path(self.temp.name)/'sheets.xlsx';reportes.export_grades(file,self.path,self.course,'3°','A')
        wb=openpyxl.load_workbook(file);wb['Calificativos'].cell(2,16,18);wb.save(file);wb.close()
        self.assertEqual(reportes.import_grades(file,self.path),1)
        with closing(sqlite3.connect(self.path)) as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],18)

    def test_primary_grade_write_cannot_target_secondary_student(self):
        with db.obtener_conexion(self.path) as conn:conn.execute("UPDATE Docente_Config SET nivel_educativo='Primaria' WHERE id=1")
        course=db.obtener_cursos(db_path=self.path)[0][0];comp=db.obtener_competencias_por_curso(course,self.path)[0][0];cap=db.obtener_capacidades_por_competencia(comp,self.path)[0][0]
        session=db.crear_o_actualizar_sesion_clase(None,course,comp,'3°','A','Primaria','',1,[(cap,'Criterio')],db_path=self.path)
        with self.assertRaises(ValueError):db.guardar_calificaciones_y_asistencia_sesion(session,[dict(estudiante_id=self.e,notas_por_capacidad={cap:20})],db_path=self.path)

    def test_repeated_primary_migration_preserves_existing_secondary_ids(self):
        with closing(sqlite3.connect(self.path)) as conn:before=conn.execute('SELECT * FROM Notas_Sesion_Capacidad').fetchall()
        db.inicializar_db(self.path)
        with closing(sqlite3.connect(self.path)) as conn:self.assertEqual(before,conn.execute('SELECT * FROM Notas_Sesion_Capacidad').fetchall())
        self.assertEqual(len(db.obtener_cursos(db_path=self.path)),10)

    def test_pdf_and_insignia_report(self):
        image=Path(self.temp.name)/'escudo.png';Image.new('RGB',(100,200),'green').save(image)
        reportes.save_logo(image,self.path)
        path=Path(self.temp.name)/'notas.pdf'
        reportes.export_grades(path,self.path,self.course,'3°','A',reportes.logo_bytes(self.path))
        self.assertTrue(path.read_bytes().startswith(b'%PDF'));self.assertGreater(path.stat().st_size,1000)

    def test_optional_scale_does_not_change_numeric_grades(self):
        from escala import save_thresholds
        self.assertEqual(db.nota_a_literal(13.2,self.path),'B')
        save_thresholds(self.path,(10,13,17))
        self.assertEqual(db.nota_a_literal(13.2,self.path),'A')
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],13.2)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Historial_Reglas').fetchone()[0],1)

    def test_document_cannot_overwrite_working_database(self):
        before=self.path.read_bytes()
        with self.assertRaises(ValueError):documento.save_document(self.path,self.path)
        self.assertEqual(before,self.path.read_bytes())
