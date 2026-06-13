import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "finanzas.db"

# ─── Catálogos ────────────────────────────────────────────────────────────────
CATEGORIAS    = ["Alimentación","Transporte","Vivienda","Servicios","Suscripción",
                 "Salud","Educación/Certs","Deseos","Ropa","Varios"]
METODOS_PAGO  = ["TC Bancolombia","TC Nubank","TD Bancolombia"]
TIPOS_INGRESO = ["Quincenal 1","Quincenal 2","Bono","Prima","Extra","Comisión","Otros"]

_DEFAULTS: dict[str, float] = {
    "ingreso_neto":        4_400_000,
    "limite_gastos_pct":   0.80,
    "meta_ahorro_pct":     0.10,
    "meta_desarrollo_pct": 0.10,
    "meta_fondo":          6_300_000,
}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _add_col(conn: sqlite3.Connection, table: str, col: str, defn: str):
    existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if col not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS gastos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                descripcion TEXT    DEFAULT '',
                categoria   TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                metodo_pago TEXT    NOT NULL,
                nota        TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS ahorros (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                concepto    TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                tipo        TEXT    NOT NULL CHECK(tipo IN ('ingreso','retiro')),
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS ingresos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                concepto    TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                tipo        TEXT    NOT NULL,
                nota        TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS fijos_estado (
                concepto    TEXT    NOT NULL,
                anio        INTEGER NOT NULL,
                mes         INTEGER NOT NULL,
                pagado      INTEGER DEFAULT 0,
                PRIMARY KEY (concepto, anio, mes)
            );
            CREATE TABLE IF NOT EXISTS pagos_tc (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                tarjeta     TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                concepto    TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS configuracion (
                clave       TEXT PRIMARY KEY,
                valor       TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bolsillo (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                concepto    TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                tipo        TEXT    NOT NULL CHECK(tipo IN ('deposito','retiro')),
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_gastos_fecha   ON gastos(fecha);
            CREATE INDEX IF NOT EXISTS idx_ingresos_fecha ON ingresos(fecha);
            CREATE INDEX IF NOT EXISTS idx_pagos_tc_fecha ON pagos_tc(fecha);
            CREATE INDEX IF NOT EXISTS idx_bolsillo_fecha ON bolsillo(fecha);
        """)
        _add_col(conn, "gastos",   "nota", "TEXT DEFAULT ''")
        _add_col(conn, "ingresos", "nota", "TEXT DEFAULT ''")
        for k, v in _DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO configuracion(clave,valor) VALUES(?,?)",
                (k, str(v)),
            )


# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

def get_config() -> dict[str, float]:
    with get_conn() as conn:
        rows = conn.execute("SELECT clave,valor FROM configuracion").fetchall()
    cfg = {r["clave"]: float(r["valor"]) for r in rows}
    return {**_DEFAULTS, **cfg}


def set_config(clave: str, valor: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO configuracion(clave,valor) VALUES(?,?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
            (clave, str(valor)),
        )


def get_derived(cfg: dict | None = None) -> dict[str, float]:
    c = cfg or get_config()
    base = c["ingreso_neto"]
    return {
        "INGRESO_NETO":          base,
        "LIMITE_GASTOS":         base * c["limite_gastos_pct"],
        "META_AHORRO":           base * c["meta_ahorro_pct"],
        "META_DESARROLLO":       base * c["meta_desarrollo_pct"],
        "META_FONDO_EMERGENCIA": c["meta_fondo"],
    }


# ─── GASTOS ───────────────────────────────────────────────────────────────────

def insertar_gasto(fecha, descripcion: str, categoria: str, monto: float,
                   metodo_pago: str, nota: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO gastos(fecha,descripcion,categoria,monto,metodo_pago,nota) "
            "VALUES(?,?,?,?,?,?)",
            (str(fecha), descripcion.strip(), categoria, float(monto), metodo_pago, nota.strip()),
        )


def editar_gasto(gasto_id: int, fecha, descripcion: str, categoria: str,
                 monto: float, metodo_pago: str, nota: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE gastos SET fecha=?,descripcion=?,categoria=?,monto=?,metodo_pago=?,nota=? "
            "WHERE id=?",
            (str(fecha), descripcion.strip(), categoria, float(monto), metodo_pago, nota.strip(), gasto_id),
        )


def eliminar_gasto(gasto_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM gastos WHERE id=?", (gasto_id,))


def obtener_gastos_mes(anio: int, mes: int) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT id,fecha,descripcion,categoria,monto,metodo_pago,nota "
            "FROM gastos "
            "WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=? "
            "ORDER BY fecha DESC, id DESC",
            conn, params=(str(anio), f"{mes:02d}"),
        )


def gasto_total_mes(anio: int, mes: int) -> float:
    df = obtener_gastos_mes(anio, mes)
    return float(df["monto"].sum()) if not df.empty else 0.0


def gasto_por_categoria_mes(anio: int, mes: int) -> pd.DataFrame:
    df = obtener_gastos_mes(anio, mes)
    if df.empty:
        return pd.DataFrame(columns=["categoria","monto"])
    return (df.groupby("categoria", as_index=False)["monto"]
              .sum().sort_values(by="monto", ascending=False))  # type: ignore[arg-type]


def gasto_por_metodo_mes(anio: int, mes: int) -> pd.DataFrame:
    df = obtener_gastos_mes(anio, mes)
    if df.empty:
        return pd.DataFrame(columns=["metodo_pago","monto"])
    return (df.groupby("metodo_pago", as_index=False)["monto"]
              .sum().sort_values(by="monto", ascending=False))  # type: ignore[arg-type]


def gastos_ultimos_meses(n: int = 6) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT strftime('%Y-%m',fecha) AS periodo, SUM(monto) AS total "
            "FROM gastos GROUP BY periodo ORDER BY periodo DESC LIMIT ?",
            conn, params=(n,),
        )


# ─── INGRESOS ─────────────────────────────────────────────────────────────────

def insertar_ingreso(fecha, concepto: str, monto: float, tipo: str, nota: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ingresos(fecha,concepto,monto,tipo,nota) VALUES(?,?,?,?,?)",
            (str(fecha), concepto.strip(), float(monto), tipo, nota.strip()),
        )


def editar_ingreso(ingreso_id: int, fecha, concepto: str, monto: float,
                   tipo: str, nota: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE ingresos SET fecha=?,concepto=?,monto=?,tipo=?,nota=? WHERE id=?",
            (str(fecha), concepto.strip(), float(monto), tipo, nota.strip(), ingreso_id),
        )


def eliminar_ingreso(ingreso_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM ingresos WHERE id=?", (ingreso_id,))


def obtener_ingresos_mes(anio: int, mes: int) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT id,fecha,concepto,monto,tipo,nota FROM ingresos "
            "WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=? "
            "ORDER BY fecha DESC, id DESC",
            conn, params=(str(anio), f"{mes:02d}"),
        )


def total_ingresos_mes(anio: int, mes: int) -> float:
    df = obtener_ingresos_mes(anio, mes)
    return float(df["monto"].sum()) if not df.empty else 0.0


def ingresos_ultimos_meses(n: int = 6) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT strftime('%Y-%m',fecha) AS periodo, SUM(monto) AS total "
            "FROM ingresos GROUP BY periodo ORDER BY periodo DESC LIMIT ?",
            conn, params=(n,),
        )


# ─── AHORROS ──────────────────────────────────────────────────────────────────

def insertar_movimiento_ahorro(fecha, concepto: str, monto: float, tipo: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ahorros(fecha,concepto,monto,tipo) VALUES(?,?,?,?)",
            (str(fecha), concepto.strip(), float(monto), tipo),
        )


def obtener_saldo_ahorro() -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END),0) AS saldo "
            "FROM ahorros"
        ).fetchone()
    return float(row["saldo"])


def obtener_movimientos_ahorro() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM ahorros ORDER BY fecha DESC, id DESC", conn
        )


def proyeccion_fondo(saldo_actual: float, ahorro_mensual: float, meta: float) -> int:
    restante = meta - saldo_actual
    if restante <= 0:
        return 0
    if ahorro_mensual <= 0:
        return -1
    return int(restante // ahorro_mensual) + 1


# ─── PAGOS TC ─────────────────────────────────────────────────────────────────

def insertar_pago_tc(fecha, tarjeta: str, monto: float, concepto: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pagos_tc(fecha,tarjeta,monto,concepto) VALUES(?,?,?,?)",
            (str(fecha), tarjeta, float(monto), concepto.strip()),
        )


def total_pagado_tc(tarjeta: str) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(monto),0) AS total FROM pagos_tc WHERE tarjeta=?",
            (tarjeta,),
        ).fetchone()
    return float(row["total"])


def total_pagado_tc_mes(anio: int, mes: int) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(monto),0) AS total FROM pagos_tc "
            "WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=?",
            (str(anio), f"{mes:02d}"),
        ).fetchone()
    return float(row["total"])


def obtener_pagos_tc() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM pagos_tc ORDER BY fecha DESC, id DESC", conn
        )


def eliminar_pago_tc(pago_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM pagos_tc WHERE id=?", (pago_id,))


def total_gastos_tc_historico(tarjeta: str) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(monto),0) AS total FROM gastos WHERE metodo_pago=?",
            (tarjeta,),
        ).fetchone()
    return float(row["total"])


# ─── FIJOS ────────────────────────────────────────────────────────────────────

def get_fijos_pagados_mes(anio: int, mes: int) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT concepto FROM fijos_estado WHERE anio=? AND mes=? AND pagado=1",
            (anio, mes),
        ).fetchall()
    return {r["concepto"] for r in rows}


def set_fijo_estado(concepto: str, anio: int, mes: int, pagado: bool):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO fijos_estado(concepto,anio,mes,pagado) VALUES(?,?,?,?) "
            "ON CONFLICT(concepto,anio,mes) DO UPDATE SET pagado=excluded.pagado",
            (concepto, anio, mes, 1 if pagado else 0),
        )


# ─── BOLSILLO ─────────────────────────────────────────────────────────────────

def insertar_bolsillo(fecha, concepto: str, monto: float, tipo: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bolsillo(fecha,concepto,monto,tipo) VALUES(?,?,?,?)",
            (str(fecha), concepto.strip(), float(monto), tipo),
        )


def obtener_saldo_bolsillo() -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='deposito' THEN monto ELSE -monto END),0) AS saldo "
            "FROM bolsillo"
        ).fetchone()
    return float(row["saldo"])


def obtener_movimientos_bolsillo() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM bolsillo ORDER BY fecha DESC, id DESC", conn
        )


def neto_bolsillo_mes(anio: int, mes: int) -> float:
    """Depósitos menos retiros del bolsillo en el mes (salida real del banco TD)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='deposito' THEN monto ELSE -monto END),0) AS neto "
            "FROM bolsillo WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=?",
            (str(anio), f"{mes:02d}"),
        ).fetchone()
    return float(row["neto"])


def eliminar_bolsillo(bolsillo_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM bolsillo WHERE id=?", (bolsillo_id,))
