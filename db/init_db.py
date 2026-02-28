import glob
import os
import psycopg

from symlib import KiCadSymLibraryParser

LIBRARY_PATH = '../'

DB_PARAMS = {
	'dbname': 'kicad',
	'user': 'kicad_admin',
	'password': os.getenv('DB_PASSWORD'),
	'host': os.getenv('DB_HOST', 'localhost'),
	'port': 5432
}

CLEAR_LEGACY_SQL = """DELETE FROM part;
DELETE FROM symbol;
DELETE FROM footprint;
DELETE FROM package;
ALTER SEQUENCE symbol_id_seq RESTART WITH 1;
ALTER SEQUENCE footprint_id_seq RESTART WITH 1;
ALTER SEQUENCE package_id_seq RESTART WITH 1;"""


def reset_db(cursor) -> None:
	cursor.execute(CLEAR_LEGACY_SQL)

def get_library_id(cursor, path: str) -> int:
	cursor.execute("SELECT id, alias FROM library WHERE path = %s", (path,))
	return cursor.fetchone()

def import_footprints(cursor, path: str, lib_id: int) -> None:
	for name in os.listdir(path):
		name, ext = os.path.splitext(name)
		if ext == '.kicad_mod':
			print(name)
			cursor.execute("INSERT INTO footprint (name, library_id, package_id) VALUES (%s, %s, %s)", (name, lib_id, None))

def import_symbols(cursor, path: str, lib_id: int) -> None:
	lib = KiCadSymLibraryParser(path)
	for symbol in lib.tree.select_children('symbol'):
		name = symbol.get_attributes()[0].strip('" \t')
		if not name.startswith('*'):
			cursor.execute("INSERT INTO symbol (name, library_id) VALUES (%s, %s)", (name, lib_id))


def main():
	db = psycopg.connect(**DB_PARAMS)
	cursor = db.cursor()

	reset_db(cursor)

	for fn in glob.glob(os.path.join(LIBRARY_PATH, '*.pretty')):
		lib_id, alias = get_library_id(cursor, os.path.basename(fn))
		import_footprints(cursor, fn, lib_id)

	for fn in glob.glob(os.path.join(LIBRARY_PATH, '*.kicad_sym')):
		lib_id, alias = get_library_id(cursor, os.path.basename(fn))
		if alias != 'Virtual':
			import_symbols(cursor, fn, lib_id)

	db.commit()
	cursor.close()
	db.close()

main()
