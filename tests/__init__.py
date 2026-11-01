"""Tests always isolate application storage from the real user profile."""
import os
import tempfile

_storage = tempfile.TemporaryDirectory(prefix='registro-tests-')
os.environ['REGISTRO_DATA_DIR'] = _storage.name
os.environ['REGISTRO_DB_PATH'] = os.path.join(_storage.name, 'gui.db')
