import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "finanzas.db"

CATEGORIAS = [
    "Alimentación", "Transporte", "Vivienda", "Servicios",
    "Suscripción", "Salud", "Educación/Certs", "Deseos", "Ropa", "Varios"
]

METODOS_PAGO = ["TC Bancolombia", "TC Nubank", "TD Bancolombia"]

TIPOS_INGRESO = ["Quincenal 1", "Quincenal 2", "Bono", "Prima", "Extra", "Comisión", "Otros"]

INGRESO_NETO = 4_400_000
LIMITE_GASTOS = int(INGRESO_NETO * 0.80)    # 3.520.000
META_AHORRO = int(INGRESO_NETO * 0.10)       # 440.000
META_DESARROLLO = int(INGRESO_NETO * 0.20)  # 880.000
META_FONDO_EMERGENCIA = 6_300_000


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS gastos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha          TEXT    NOT NULL,
                descripcion    TEXT    DEFAULT '',
                categoria      TEXT    NOT NULL,
                monto          REAL    NOT NULL,
                metodo_pago    TEXT    NOT NULL,
                created_at     TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS ahorros (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha          TEXT    NOT NULL,
                concepto       TEXT    NOT NULL,
                monto          REAL    NOT NULL,
                tipo           TEXT    NOT NULL CHECK(tipo IN ('ingreso','retiro')),
                created_at     TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS ingresos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha          TEXT    NOT NULL,
                concepto       TEXT    NOT NULL,
                monto          REAL    NOT NULL,
                tipo           TEXT    NOT NULL,
                created_at     TEXT    DEFAULT (datetime('now','localtime'))
            );
        """)


# ─── GASTOS ───────────────────────────────────────────────────────────────────

def insertar_gasto(fecha, descripcion, categoria, monto, metodo_pago):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO gastos (fecha, descripcion, categoria, monto, metodo_pago) VALUES (?,?,?,?,?)",
            (str(fecha), descripcion.strip(), categoria, float(monto), metodo_pago)
        )


def obtener_gastos_mes(anio: int, mes: int) -> pd.DataFrame:
    query = """
        SELECT id, fecha, descripcion, categoria, monto, metodo_pago
        FROM gastos
        WHERE strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
        ORDER BY fecha DESC, id DESC
    """
    with get_conn() as conn:
        df = pd.read_sql_query(query, conn, params=(str(anio), f"{mes:02d}"))
    return df


def obtener_todos_gastos() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM gastos ORDER BY fecha DESC, id DESC", conn
        )


def eliminar_gasto(gasto_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))


# ─── AHORROS ──────────────────────────────────────────────────────────────────

def insertar_movimiento_ahorro(fecha, concepto, monto, tipo):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ahorros (fecha, concepto, monto, tipo) VALUES (?,?,?,?)",
            (str(fecha), concepto.strip(), float(monto), tipo)
        )


def obtener_saldo_ahorro() -> float:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(
                SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END), 0
            ) AS saldo FROM ahorros
        """).fetchone()
    return row["saldo"]


def obtener_movimientos_ahorro() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM ahorros ORDER BY fecha DESC, id DESC", conn
        )


# ─── HELPERS ANALÍTICOS ───────────────────────────────────────────────────────

def gasto_total_mes(anio: int, mes: int) -> float:
    df = obtener_gastos_mes(anio, mes)
    return df["monto"].sum() if not df.empty else 0.0


def gasto_por_categoria_mes(anio: int, mes: int) -> pd.DataFrame:
    df = obtener_gastos_mes(anio, mes)
    if df.empty:
        return pd.DataFrame(columns=["categoria", "monto"])
    return df.groupby("categoria", as_index=False)["monto"].sum().sort_values("monto", ascending=False)


def gasto_por_metodo_mes(anio: int, mes: int) -> pd.DataFrame:
    df = obtener_gastos_mes(anio, mes)
    if df.empty:
        return pd.DataFrame(columns=["metodo_pago", "monto"])
    return df.groupby("metodo_pago", as_index=False)["monto"].sum().sort_values("monto", ascending=False)


# ─── INGRESOS ─────────────────────────────────────────────────────────────────

def insertar_ingreso(fecha, concepto: str, monto: float, tipo: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ingresos (fecha, concepto, monto, tipo) VALUES (?,?,?,?)",
            (str(fecha), concepto.strip(), float(monto), tipo)
        )


def obtener_ingresos_mes(anio: int, mes: int) -> pd.DataFrame:
    query = """
        SELECT id, fecha, concepto, monto, tipo
        FROM ingresos
        WHERE strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
        ORDER BY fecha DESC, id DESC
    """
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=(str(anio), f"{mes:02d}"))


def total_ingresos_mes(anio: int, mes: int) -> float:
    df = obtener_ingresos_mes(anio, mes)
    return df["monto"].sum() if not df.empty else 0.0


def eliminar_ingreso(ingreso_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM ingresos WHERE id = ?", (ingreso_id,))


def proyeccion_fondo(saldo_actual: float, ahorro_mensual: float) -> int:
    """Devuelve meses restantes para completar el fondo. -1 si ahorro es 0."""
    restante = META_FONDO_EMERGENCIA - saldo_actual
    if restante <= 0:
        return 0
    if ahorro_mensual <= 0:
        return -1
    return int(restante // ahorro_mensual) + 1
