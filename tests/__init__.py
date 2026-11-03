"""Tests always isolate application storage from the real user profile."""
import os
import tempfile

_storage = tempfile.TemporaryDirectory(prefix='registro-tests-')
os.environ['REGISTRO_DATA_DIR'] = _storage.name
os.environ['REGISTRO_DB_PATH'] = os.path.join(_storage.name, 'gui.db')


def populate_student_template(path):
    """Explicit test-only roster; production templates are empty."""
    import openpyxl
    wb=openpyxl.load_workbook(path)
    for n in range(1,4):wb.active.append([None,f"Fixture {n}",f"Alumno {n}","3°","A","ACTIVO"])
    wb.save(path);wb.close()
