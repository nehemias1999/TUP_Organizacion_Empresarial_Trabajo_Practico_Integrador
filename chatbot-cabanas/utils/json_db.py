import json
import os
import sqlite3

BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(BASE, "laspircas.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cabanas (
                id                  TEXT PRIMARY KEY,
                nombre              TEXT NOT NULL,
                capacidad_max       INTEGER NOT NULL,
                precio_base_noche   REAL NOT NULL,
                descripcion         TEXT DEFAULT '',
                amenities           TEXT DEFAULT '[]',
                activa              INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS reservas (
                codigo_reserva      TEXT PRIMARY KEY,
                cabana_id           TEXT NOT NULL,
                checkin             TEXT NOT NULL,
                checkout            TEXT NOT NULL,
                noches              INTEGER NOT NULL,
                personas            INTEGER NOT NULL,
                estado              TEXT NOT NULL,
                huesped_dni         TEXT,
                huesped             TEXT NOT NULL,
                precios             TEXT NOT NULL,
                pago                TEXT NOT NULL,
                resena_solicitada   INTEGER DEFAULT 0,
                historial_estados   TEXT DEFAULT '[]',
                timestamps          TEXT DEFAULT '{}',
                notas_admin         TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_res_cabana ON reservas (cabana_id);
            CREATE INDEX IF NOT EXISTS idx_res_estado ON reservas (estado);
            CREATE INDEX IF NOT EXISTS idx_res_dni    ON reservas (huesped_dni);

            CREATE TABLE IF NOT EXISTS sesiones (
                chat_id TEXT PRIMARY KEY,
                datos   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS secuencias (
                nombre TEXT PRIMARY KEY,
                valor  INTEGER NOT NULL DEFAULT 0
            );
        """)
    _migrar_desde_json()


def _migrar_desde_json():
    """Importa los JSON existentes la primera vez que se crea la DB."""

    def _json(nombre):
        path = os.path.join(BASE, f"{nombre}.json")
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    with _conn() as conn:
        # Cabañas
        if conn.execute("SELECT COUNT(*) FROM cabanas").fetchone()[0] == 0:
            data = _json("cabanas")
            if data:
                for c in data.get("cabanas", []):
                    conn.execute(
                        "INSERT OR IGNORE INTO cabanas "
                        "(id, nombre, capacidad_max, precio_base_noche, descripcion, amenities, activa) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (c["id"], c["nombre"], c["capacidad_max"], c["precio_base_noche"],
                         c.get("descripcion", ""), json.dumps(c.get("amenities", [])),
                         int(c.get("activa", True)))
                    )

        # Tarifas
        if conn.execute("SELECT COUNT(*) FROM config WHERE clave='tarifas'").fetchone()[0] == 0:
            data = _json("tarifas")
            if data:
                conn.execute(
                    "INSERT OR IGNORE INTO config (clave, valor) VALUES ('tarifas', ?)",
                    (json.dumps(data),)
                )

        # Reservas
        if conn.execute("SELECT COUNT(*) FROM reservas").fetchone()[0] == 0:
            data = _json("reservas")
            ultimo = data.get("ultimo_numero", 0) if data else 0
            conn.execute(
                "INSERT OR IGNORE INTO secuencias (nombre, valor) VALUES ('reservas', ?)",
                (ultimo,)
            )
            if data:
                for r in data.get("reservas", []):
                    conn.execute(
                        "INSERT OR IGNORE INTO reservas "
                        "(codigo_reserva, cabana_id, checkin, checkout, noches, personas, estado, "
                        " huesped_dni, huesped, precios, pago, resena_solicitada, "
                        " historial_estados, timestamps, notas_admin) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            r["codigo_reserva"], r["cabana_id"],
                            r["fechas"]["checkin"], r["fechas"]["checkout"],
                            r["fechas"]["noches"], r["personas"], r["estado"],
                            r.get("huesped", {}).get("dni"),
                            json.dumps(r.get("huesped", {})),
                            json.dumps(r.get("precios", {})),
                            json.dumps(r.get("pago", {})),
                            int(r.get("resena_solicitada", False)),
                            json.dumps(r.get("historial_estados", [])),
                            json.dumps(r.get("timestamps", {})),
                            r.get("notas_admin", ""),
                        )
                    )

        # Sesiones
        if conn.execute("SELECT COUNT(*) FROM sesiones").fetchone()[0] == 0:
            data = _json("sesiones")
            if data:
                for chat_id, sesion in data.get("sesiones", {}).items():
                    conn.execute(
                        "INSERT OR IGNORE INTO sesiones (chat_id, datos) VALUES (?, ?)",
                        (chat_id, json.dumps(sesion))
                    )


# ── Conversores ─────────────────────────────────────────────

def _row_to_cabana(row):
    return {
        "id": row["id"],
        "nombre": row["nombre"],
        "capacidad_max": row["capacidad_max"],
        "precio_base_noche": row["precio_base_noche"],
        "descripcion": row["descripcion"] or "",
        "amenities": json.loads(row["amenities"]),
        "activa": bool(row["activa"]),
    }


def _row_to_reserva(row):
    return {
        "codigo_reserva": row["codigo_reserva"],
        "cabana_id": row["cabana_id"],
        "huesped": json.loads(row["huesped"]),
        "fechas": {
            "checkin": row["checkin"],
            "checkout": row["checkout"],
            "noches": row["noches"],
            "checkin_hora": "10:00",
            "checkout_hora": "10:00",
        },
        "personas": row["personas"],
        "precios": json.loads(row["precios"]),
        "pago": json.loads(row["pago"]),
        "estado": row["estado"],
        "resena_solicitada": bool(row["resena_solicitada"]),
        "historial_estados": json.loads(row["historial_estados"]),
        "timestamps": json.loads(row["timestamps"]),
        "notas_admin": row["notas_admin"] or "",
    }


# ── Sesiones ────────────────────────────────────────────────

def get_sesion(chat_id):
    with _conn() as conn:
        row = conn.execute(
            "SELECT datos FROM sesiones WHERE chat_id = ?", (str(chat_id),)
        ).fetchone()
        return json.loads(row["datos"]) if row else None


def guardar_sesion(chat_id, sesion):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sesiones (chat_id, datos) VALUES (?, ?)",
            (str(chat_id), json.dumps(sesion, default=str))
        )


def eliminar_sesion(chat_id):
    with _conn() as conn:
        conn.execute("DELETE FROM sesiones WHERE chat_id = ?", (str(chat_id),))


# ── Cabañas ─────────────────────────────────────────────────

def get_cabanas():
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM cabanas").fetchall()
        return [_row_to_cabana(row) for row in rows]


# ── Tarifas ─────────────────────────────────────────────────

def get_tarifas():
    with _conn() as conn:
        row = conn.execute(
            "SELECT valor FROM config WHERE clave = 'tarifas'"
        ).fetchone()
        return json.loads(row["valor"]) if row else {}


# ── Reservas ────────────────────────────────────────────────

def get_reservas():
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM reservas").fetchall()
        num = conn.execute(
            "SELECT valor FROM secuencias WHERE nombre = 'reservas'"
        ).fetchone()
        return {
            "reservas": [_row_to_reserva(r) for r in rows],
            "ultimo_numero": num["valor"] if num else 0,
        }


def guardar_reserva(reserva):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO reservas "
            "(codigo_reserva, cabana_id, checkin, checkout, noches, personas, estado, "
            " huesped_dni, huesped, precios, pago, resena_solicitada, "
            " historial_estados, timestamps, notas_admin) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                reserva["codigo_reserva"], reserva["cabana_id"],
                reserva["fechas"]["checkin"], reserva["fechas"]["checkout"],
                reserva["fechas"]["noches"], reserva["personas"], reserva["estado"],
                reserva.get("huesped", {}).get("dni"),
                json.dumps(reserva.get("huesped", {})),
                json.dumps(reserva.get("precios", {})),
                json.dumps(reserva.get("pago", {})),
                int(reserva.get("resena_solicitada", False)),
                json.dumps(reserva.get("historial_estados", [])),
                json.dumps(reserva.get("timestamps", {})),
                reserva.get("notas_admin", ""),
            )
        )
        conn.execute(
            "UPDATE secuencias SET valor = valor + 1 WHERE nombre = 'reservas'"
        )
        row = conn.execute(
            "SELECT valor FROM secuencias WHERE nombre = 'reservas'"
        ).fetchone()
        return row["valor"]


def actualizar_reserva(codigo, campos):
    reserva = buscar_reserva(codigo)
    if not reserva:
        return
    for k, v in campos.items():
        reserva[k] = v
    with _conn() as conn:
        conn.execute(
            "UPDATE reservas SET "
            "cabana_id=?, checkin=?, checkout=?, noches=?, personas=?, estado=?, "
            "huesped_dni=?, huesped=?, precios=?, pago=?, resena_solicitada=?, "
            "historial_estados=?, timestamps=?, notas_admin=? "
            "WHERE codigo_reserva=?",
            (
                reserva["cabana_id"],
                reserva["fechas"]["checkin"],
                reserva["fechas"]["checkout"],
                reserva["fechas"]["noches"],
                reserva["personas"],
                reserva["estado"],
                reserva.get("huesped", {}).get("dni"),
                json.dumps(reserva.get("huesped", {})),
                json.dumps(reserva.get("precios", {})),
                json.dumps(reserva.get("pago", {})),
                int(reserva.get("resena_solicitada", False)),
                json.dumps(reserva.get("historial_estados", [])),
                json.dumps(reserva.get("timestamps", {})),
                reserva.get("notas_admin", ""),
                codigo,
            )
        )


def buscar_reserva(codigo):
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM reservas WHERE codigo_reserva = ?", (codigo,)
        ).fetchone()
        return _row_to_reserva(row) if row else None


def hay_solapamiento(cabana_id, checkin, checkout, estados_ocupados):
    """True si existe una reserva activa que se solapa con el rango dado."""
    ci = checkin.isoformat()
    co = checkout.isoformat()
    placeholders = ",".join("?" * len(estados_ocupados))
    with _conn() as conn:
        row = conn.execute(
            f"SELECT 1 FROM reservas "
            f"WHERE cabana_id = ? AND estado IN ({placeholders}) "
            f"AND checkin < ? AND checkout > ? "
            f"LIMIT 1",
            (cabana_id, *list(estados_ocupados), co, ci)
        ).fetchone()
        return row is not None


# ── Bootstrap ────────────────────────────────────────────────
_init_db()
