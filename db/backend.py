import os
import asyncpg
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, PlainTextResponse
from starlette.routing import Route
from starlette.status import (
	HTTP_200_OK,
	HTTP_201_CREATED,
	HTTP_400_BAD_REQUEST,
	HTTP_401_UNAUTHORIZED,
	HTTP_404_NOT_FOUND,
	HTTP_500_INTERNAL_SERVER_ERROR
)


# ──────────────────────────────────────────────────────────────
#   Reusable async DB helpers (replaces old KiCadDB methods)
# ──────────────────────────────────────────────────────────────

# ─── Library ──────────────────────────────────────────────────

async def set_library(
conn: asyncpg.Connection,
type_: str,
alias: str,
path: str
) -> int:
	"""Insert or update library and return its id"""
	row = await conn.fetchrow(
		"""
        INSERT
        INTO library (type, alias, path)
        VALUES ($1, $2, $3)
        ON CONFLICT (type, alias) DO UPDATE
            SET path = excluded.path
        RETURNING id
		""",
		type_, alias, path
	)
	return row['id']


async def get_library(
conn: asyncpg.Connection,
lib_id: Optional[int] = None,
alias: Optional[str] = None,
path: Optional[str] = None
) -> Optional[Dict[str, Any]] | List[Dict[str, Any]]:
	"""Fetch a single library by id, alias, or path (first match), or all libraries if no filters provided"""
	if not any((lib_id, alias, path)):
		query = "SELECT id, type, alias, path FROM library ORDER BY id"
		rows = await conn.fetch(query)
		return [dict(row) for row in rows]

	conditions = []
	params: List[Any] = []

	if lib_id is not None:
		conditions.append("id = $%d" % (len(params) + 1))
		params.append(lib_id)
	if alias is not None:
		conditions.append("alias = $%d" % (len(params) + 1))
		params.append(alias)
	if path is not None:
		conditions.append("path = $%d" % (len(params) + 1))
		params.append(path)

	query = """
        SELECT id, type, alias, path
        FROM library
        WHERE {}
    """.format(" AND ".join(conditions))

	row = await conn.fetchrow(query, *params)
	return dict(row) if row else None


async def delete_library(
conn: asyncpg.Connection,
lib_id: int
) -> bool:
	"""Delete library by id"""
	result = await conn.execute(
		"DELETE FROM library WHERE id = $1",
		lib_id
	)
	return result == "DELETE 1"


async def set_package(
conn: asyncpg.Connection,
name: str
) -> Optional[int]:
	"""Insert package if not exists, return id or None if already existed"""
	row = await conn.fetchrow(
		"""
        INSERT
        INTO package (name)
        VALUES ($1)
        ON CONFLICT (name) DO NOTHING
        RETURNING id
		""",
		name
	)
	return row['id'] if row else None


async def get_package(
conn: asyncpg.Connection,
package_id: Optional[int] = None,
name: Optional[str] = None
) -> Optional[Dict[str, Any]] | List[Dict[str, Any]]:
	if package_id is None and name is None:
		query = "SELECT id, name FROM package ORDER BY id"
		rows = await conn.fetch(query)
		return [dict(row) for row in rows]

	conditions = []
	params: List[Any] = []

	if package_id is not None:
		conditions.append("id = $%d" % (len(params) + 1))
		params.append(package_id)
	if name is not None:
		conditions.append("name = $%d" % (len(params) + 1))
		params.append(name)

	query = """
        SELECT id, name
        FROM package
        WHERE {}
    """.format(" AND ".join(conditions))

	row = await conn.fetchrow(query, *params)
	return dict(row) if row else None


async def delete_package(
conn: asyncpg.Connection,
package_id: int
) -> bool:
	result = await conn.execute(
		"DELETE FROM package WHERE id = $1",
		package_id
	)
	return result == "DELETE 1"


async def set_footprint(
conn: asyncpg.Connection,
name: str,
library_id: int,
package_id: Optional[int]
) -> int:
	row = await conn.fetchrow(
		"""
        INSERT
        INTO footprint (name, library_id, package_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (name) DO UPDATE
            SET library_id = excluded.library_id,
                package_id = excluded.package_id
        RETURNING id
		""",
		name, library_id, package_id
	)
	return row['id']


async def get_footprint(
conn: asyncpg.Connection,
footprint_id: Optional[int] = None,
name: Optional[str] = None
) -> Optional[Dict[str, Any]] | List[Dict[str, Any]]:
	if footprint_id is None and name is None:
		query = "SELECT id, name, library_id, package_id FROM footprint ORDER BY id"
		rows = await conn.fetch(query)
		return [dict(row) for row in rows]

	conditions = []
	params: List[Any] = []

	if footprint_id is not None:
		conditions.append("id = $%d" % (len(params) + 1))
		params.append(footprint_id)
	if name is not None:
		conditions.append("name = $%d" % (len(params) + 1))
		params.append(name)

	query = """
        SELECT id, name, library_id, package_id
        FROM footprint
        WHERE {}
    """.format(" AND ".join(conditions))

	row = await conn.fetchrow(query, *params)
	return dict(row) if row else None


async def delete_footprint(
conn: asyncpg.Connection,
footprint_id: int
) -> bool:
	result = await conn.execute(
		"DELETE FROM footprint WHERE id = $1",
		footprint_id
	)
	return result == "DELETE 1"


async def set_symbol(
conn: asyncpg.Connection,
name: str,
library_id: int
) -> int:
	row = await conn.fetchrow(
		"""
        INSERT
        INTO symbol (name, library_id)
        VALUES ($1, $2)
        ON CONFLICT (name) DO UPDATE
            SET library_id = excluded.library_id
        RETURNING id
		""",
		name, library_id
	)
	return row['id']


async def get_symbol(
conn: asyncpg.Connection,
symbol_id: Optional[int] = None,
name: Optional[str] = None
) -> Optional[Dict[str, Any]] | List[Dict[str, Any]]:
	if symbol_id is None and name is None:
		query = "SELECT id, name, library_id FROM symbol ORDER BY id"
		rows = await conn.fetch(query)
		return [dict(row) for row in rows]

	conditions = []
	params: List[Any] = []

	if symbol_id is not None:
		conditions.append("id = $%d" % (len(params) + 1))
		params.append(symbol_id)
	if name is not None:
		conditions.append("name = $%d" % (len(params) + 1))
		params.append(name)

	query = """
        SELECT id, name, library_id
        FROM symbol
        WHERE {}
    """.format(" AND ".join(conditions))

	row = await conn.fetchrow(query, *params)
	return dict(row) if row else None


async def delete_symbol(
conn: asyncpg.Connection,
symbol_id: int
) -> bool:
	result = await conn.execute(
		"DELETE FROM symbol WHERE id = $1",
		symbol_id
	)
	return result == "DELETE 1"


async def set_part(
conn: asyncpg.Connection,
partnumber: str,
symbol_id: int,
footprint_id: int,
value: Optional[str] = None,
description: Optional[str] = None,
datasheet: Optional[str] = None,
exclude_bom: bool = False,
exclude_pcb: bool = False,
lcsc_num: Optional[str] = None,
chipdip_num: Optional[int] = None
) -> str:
	row = await conn.fetchrow(
		"""
        INSERT
        INTO part (
            partnumber, symbol_id, footprint_id, value, description,
            datasheet, exclude_bom, exclude_pcb, lcsc_num, chipdip_num)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (partnumber) DO UPDATE SET symbol_id = excluded.symbol_id,
            footprint_id = excluded.footprint_id,
            value = excluded.value,
            description = excluded.description,
            datasheet = excluded.datasheet,
            exclude_bom = excluded.exclude_bom,
            exclude_pcb = excluded.exclude_pcb,
            lcsc_num = excluded.lcsc_num,
            chipdip_num = excluded.chipdip_num
        RETURNING partnumber
		""",
		partnumber, symbol_id, footprint_id, value, description,
		datasheet, exclude_bom, exclude_pcb, lcsc_num, chipdip_num
	)
	return row['partnumber']


async def get_part(
conn: asyncpg.Connection,
partnumber: Optional[str] = None
) -> Optional[Dict[str, Any]] | List[Dict[str, Any]]:
	if partnumber is None:
		rows = await conn.fetch("SELECT * FROM part ORDER BY partnumber")
		return [dict(row) for row in rows]

	row = await conn.fetchrow(
		"SELECT * FROM part WHERE partnumber = $1",
		partnumber
	)
	return dict(row) if row else None


async def delete_part(
conn: asyncpg.Connection,
partnumber: str
) -> bool:
	result = await conn.execute(
		"DELETE FROM part WHERE partnumber = $1",
		partnumber
	)
	return result == "DELETE 1"


async def get_kicad_view(
conn: asyncpg.Connection,
partnumber: Optional[str] = None,
limit: int = 200
) -> List[Dict[str, Any]]:
	query = "SELECT * FROM kicad"
	params: List[Any] = []

	if partnumber:
		query += " WHERE partnumber ILIKE $1"
		params.append(f"%{partnumber}%")

	query += " ORDER BY partnumber LIMIT $%d" % (len(params) + 1)
	params.append(limit)

	rows = await conn.fetch(query, *params)
	return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────
#   Authentication stub (very simple for now – replace later)
# ──────────────────────────────────────────────────────────────

async def require_auth(request: Request) -> None:
	"""
	Simple API key check – for demo / development only.
	In production → use JWT / OAuth2 / API keys stored in DB / secrets manager
	"""
	api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
	if not api_key:
		raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Authorization required")

	# For now – hardcoded value (CHANGE THIS!)
	expected_key = os.getenv("API_KEY", "dev-secret-key-123456")

	if api_key != expected_key and api_key != f"Bearer {expected_key}":
		raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid API key")


# ──────────────────────────────────────────────────────────────
#   Endpoints
# ──────────────────────────────────────────────────────────────

async def health_check(request: Request) -> Response:
	return JSONResponse({"status": "ok"})


# ─── Library ──────────────────────────────────────────────────

async def create_or_update_library(request: Request) -> Response:
	await require_auth(request)
	try:
		data = await request.json()
		type_ = data.get("type")
		alias = data.get("alias")
		path = data.get("path")

		if not all([type_, alias, path]):
			return JSONResponse({"error": "Missing required fields"}, status_code=HTTP_400_BAD_REQUEST)

		pool = app.state.db_pool
		async with pool.acquire() as conn:
			lib_id = await set_library(type_, alias, path, conn)
			return JSONResponse({"id": lib_id}, status_code=HTTP_201_CREATED)
	except Exception as e:
		return JSONResponse({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)


async def get_library_endpoint(request: Request) -> Response:
	await require_auth(request)
	lib_id = request.query_params.get("id")
	alias = request.query_params.get("alias")
	path = request.query_params.get("path")

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		lib = await get_library(
			conn,
			lib_id=int(lib_id) if lib_id else None,
			alias=alias,
			path=path
		)
		if not lib:
			return JSONResponse({"error": "Library not found"}, status_code=HTTP_404_NOT_FOUND)
		return JSONResponse(lib)


async def delete_library_endpoint(request: Request) -> Response:
	await require_auth(request)
	lib_id = request.path_params.get("lib_id")
	if not lib_id:
		return JSONResponse({"error": "Missing lib_id"}, status_code=HTTP_400_BAD_REQUEST)

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		deleted = await delete_library(conn, int(lib_id))
		if not deleted:
			return JSONResponse({"error": "Library not found"}, status_code=HTTP_404_NOT_FOUND)
		return PlainTextResponse("Deleted", status_code=HTTP_200_OK)


# ─── Package ──────────────────────────────────────────────────

async def create_package(request: Request) -> Response:
	await require_auth(request)
	try:
		data = await request.json()
		name = data.get("name")
		if not name:
			return JSONResponse({"error": "Missing name"}, status_code=HTTP_400_BAD_REQUEST)

		pool = app.state.db_pool
		async with pool.acquire() as conn:
			pkg_id = await set_package(conn, name)
			if pkg_id is None:
				return JSONResponse({"message": "Package already exists"}, status_code=HTTP_200_OK)
			return JSONResponse({"id": pkg_id}, status_code=HTTP_201_CREATED)
	except Exception as e:
		return JSONResponse({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)


async def get_package_endpoint(request: Request) -> Response:
	await require_auth(request)
	pkg_id = request.query_params.get("id")
	name = request.query_params.get("name")

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		pkg = await get_package(conn, int(pkg_id) if pkg_id else None, name)
		if not pkg:
			return JSONResponse({"error": "Package not found"}, status_code=HTTP_404_NOT_FOUND)
		return JSONResponse(pkg)


async def delete_package_endpoint(request: Request) -> Response:
	await require_auth(request)
	pkg_id = request.path_params.get("pkg_id")
	if not pkg_id:
		return JSONResponse({"error": "Missing package id"}, status_code=HTTP_400_BAD_REQUEST)

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		deleted = await delete_package(conn, int(pkg_id))
		if not deleted:
			return JSONResponse({"error": "Package not found"}, status_code=HTTP_404_NOT_FOUND)
		return PlainTextResponse("Deleted", status_code=HTTP_200_OK)


# ─── Footprint ────────────────────────────────────────────────

async def create_or_update_footprint(request: Request) -> Response:
	await require_auth(request)
	try:
		data = await request.json()
		name = data.get("name")
		library_id = data.get("library_id")
		package_id = data.get("package_id")

		if not name or not library_id:
			return JSONResponse({"error": "Missing name or library_id"}, status_code=HTTP_400_BAD_REQUEST)

		pool = app.state.db_pool
		async with pool.acquire() as conn:
			fp_id = await set_footprint(conn, name, int(library_id), package_id)
			return JSONResponse({"id": fp_id}, status_code=HTTP_201_CREATED)
	except Exception as e:
		return JSONResponse({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)


async def get_footprint_endpoint(request: Request) -> Response:
	await require_auth(request)
	fp_id = request.query_params.get("id")
	name = request.query_params.get("name")

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		fp = await get_footprint(conn, int(fp_id) if fp_id else None, name)
		if not fp:
			return JSONResponse({"error": "Footprint not found"}, status_code=HTTP_404_NOT_FOUND)
		return JSONResponse(fp)


async def delete_footprint_endpoint(request: Request) -> Response:
	await require_auth(request)
	fp_id = request.path_params.get("fp_id")
	if not fp_id:
		return JSONResponse({"error": "Missing footprint id"}, status_code=HTTP_400_BAD_REQUEST)

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		deleted = await delete_footprint(conn, int(fp_id))
		if not deleted:
			return JSONResponse({"error": "Footprint not found"}, status_code=HTTP_404_NOT_FOUND)
		return PlainTextResponse("Deleted", status_code=HTTP_200_OK)


# ─── Symbol ───────────────────────────────────────────────────

async def create_or_update_symbol(request: Request) -> Response:
	await require_auth(request)
	try:
		data = await request.json()
		name = data.get("name")
		library_id = data.get("library_id")

		if not name or not library_id:
			return JSONResponse({"error": "Missing name or library_id"}, status_code=HTTP_400_BAD_REQUEST)

		pool = app.state.db_pool
		async with pool.acquire() as conn:
			sym_id = await set_symbol(conn, name, int(library_id))
			return JSONResponse({"id": sym_id}, status_code=HTTP_201_CREATED)
	except Exception as e:
		return JSONResponse({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)


async def get_symbol_endpoint(request: Request) -> Response:
	await require_auth(request)
	sym_id = request.query_params.get("id")
	name = request.query_params.get("name")

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		sym = await get_symbol(conn, int(sym_id) if sym_id else None, name)
		if not sym:
			return JSONResponse({"error": "Symbol not found"}, status_code=HTTP_404_NOT_FOUND)
		return JSONResponse(sym)


async def delete_symbol_endpoint(request: Request) -> Response:
	await require_auth(request)
	sym_id = request.path_params.get("sym_id")
	if not sym_id:
		return JSONResponse({"error": "Missing symbol id"}, status_code=HTTP_400_BAD_REQUEST)

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		deleted = await delete_symbol(conn, int(sym_id))
		if not deleted:
			return JSONResponse({"error": "Symbol not found"}, status_code=HTTP_404_NOT_FOUND)
		return PlainTextResponse("Deleted", status_code=HTTP_200_OK)


# ─── Part ─────────────────────────────────────────────────────

async def create_or_update_part(request: Request) -> Response:
	await require_auth(request)
	try:
		data = await request.json()
		partnumber = data.get("partnumber")
		symbol_id = data.get("symbol_id")
		footprint_id = data.get("footprint_id")

		if not all([partnumber, symbol_id, footprint_id]):
			return JSONResponse({"error": "Missing required fields"}, status_code=HTTP_400_BAD_REQUEST)

		pool = app.state.db_pool
		async with pool.acquire() as conn:
			pn = await set_part(
				conn,
				partnumber=partnumber,
				symbol_id=int(symbol_id),
				footprint_id=int(footprint_id),
				value=data.get("value"),
				description=data.get("description"),
				datasheet=data.get("datasheet"),
				exclude_bom=data.get("exclude_bom", False),
				exclude_pcb=data.get("exclude_pcb", False),
				lcsc_num=data.get("lcsc_num"),
				chipdip_num=data.get("chipdip_num")
			)
			return JSONResponse({"partnumber": pn}, status_code=HTTP_201_CREATED)
	except Exception as e:
		return JSONResponse({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)


async def get_part_endpoint(request: Request) -> Response:
	# No auth required for read-only lookup (common pattern)
	# await require_auth(request)   ← uncomment if you want auth here too

	partnumber = request.path_params.get("partnumber")

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		part = await get_part(conn, partnumber)
		if not part:
			return JSONResponse({"error": "Part not found"}, status_code=HTTP_404_NOT_FOUND)
		return JSONResponse(part)


async def delete_part_endpoint(request: Request) -> Response:
	await require_auth(request)
	partnumber = request.path_params.get("part_id")
	if not partnumber:
		return JSONResponse({"error": "Missing partnumber"}, status_code=HTTP_400_BAD_REQUEST)

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		deleted = await delete_part(conn, partnumber)
		if not deleted:
			return JSONResponse({"error": "Part not found"}, status_code=HTTP_404_NOT_FOUND)
		return PlainTextResponse("Deleted", status_code=HTTP_200_OK)


async def search_parts_endpoint(request: Request) -> Response:
	# No auth required for search (common for public catalog)
	# await require_auth(request)   ← uncomment if needed

	q = request.query_params.get("q", "").strip()
	if not q:
		return JSONResponse({"error": "Missing ?q= parameter"}, status_code=HTTP_400_BAD_REQUEST)

	pool = app.state.db_pool
	async with pool.acquire() as conn:
		results = await get_kicad_view(conn, partnumber=q)
		return JSONResponse({"results": results, "count": len(results)})


# ──────────────────────────────────────────────────────────────
#   Routes
# ──────────────────────────────────────────────────────────────

routes = [
	Route("/health", health_check),

	# Library
	Route("/library", create_or_update_library, methods=["POST"]),
	Route("/library", get_library_endpoint, methods=["GET"]),
	Route("/library/{lib_id:int}", delete_library_endpoint, methods=["DELETE"]),

	# Package
	Route("/package", create_package, methods=["POST"]),
	Route("/package", get_package_endpoint, methods=["GET"]),
	Route("/package/{pkg_id:int}", delete_package_endpoint, methods=["DELETE"]),

	# Footprint
	Route("/footprint", create_or_update_footprint, methods=["POST"]),
	Route("/footprint", get_footprint_endpoint, methods=["GET"]),
	Route("/footprint/{fp_id:int}", delete_footprint_endpoint, methods=["DELETE"]),

	# Symbol
	Route("/symbol", create_or_update_symbol, methods=["POST"]),
	Route("/symbol", get_symbol_endpoint, methods=["GET"]),
	Route("/symbol/{sym_id:int}", delete_symbol_endpoint, methods=["DELETE"]),

	# Part
	Route("/part", create_or_update_part, methods=["POST"]),
	Route("/part", get_part_endpoint, methods=["GET"]),
	Route("/part/{partnumber}", delete_part_endpoint, methods=["DELETE"]),

	Route("/search", search_parts_endpoint, methods=["GET"]),
]


# ──────────────────────────────────────────────────────────────
#   App + Lifespan (pool management)
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: Starlette):
	"""Manage asyncpg pool lifecycle"""
	db_params = {
		"database": os.getenv("DB_NAME", "kicad"),
		"user": os.getenv("DB_USER", "kicad_admin"),
		"password": os.getenv("DB_PASSWORD"),
		"host": os.getenv("DB_HOST", "localhost"),
		"port": int(os.getenv("DB_PORT", "5432")),
		# Recommended production tuning (adjust based on your workload / server)
		"min_size": 4,  # base connections
		"max_size": 20,  # max connections (should be < DB max_connections)
		"max_queries": 50000,  # recycle after N queries
		"max_inactive_connection_lifetime": 300.0,  # close idle after 5 min
		"timeout": 30,  # acquire timeout
	}

	print("Creating asyncpg connection pool...")
	pool = await asyncpg.create_pool(**db_params)
	application.state.db_pool = pool

	yield  # ← application runs here

	print("Closing asyncpg connection pool...")
	await pool.close()


app = Starlette(
	debug=os.getenv("DEBUG", "false").lower() == "true",
	routes=routes,
	lifespan=lifespan,
)

# ─── Add CORS middleware ──────────────────────────────────────

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://127.0.0.1",
		"*"  # use wildcard for dev only (less secure)
	],
	allow_credentials=True,
	allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
	allow_headers=["Content-Type", "X-API-Key", "Authorization"],
	expose_headers=[],
	max_age=600,
)

# ──────────────────────────────────────────────────────────────
#   Development / debug server
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
	import uvicorn

	print("Starting development server → http://127.0.0.1:8888")

	uvicorn.run(
		"backend:app",
		host="127.0.0.1",
		port=8888,
		reload=True,
		log_level="info",
	)
