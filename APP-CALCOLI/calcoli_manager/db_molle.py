from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class SpringMaterial:
    id: int
    code: str
    name: str
    e_mpa: float
    g_mpa: float
    tau_amm_mpa: float
    sigma_amm_mpa: float
    notes: str


@dataclass(frozen=True)
class DiscSpringStandard:
    id: int
    code: str
    name: str
    do_mm: float
    di_mm: float
    t_mm: float
    h0_mm: float
    notes: str


DEFAULT_MATERIALS: tuple[tuple[str, str, float, float, float, float, str], ...] = (
    (
        "EN10270-SM",
        "EN 10270-1 SM",
        206000.0,
        81500.0,
        550.0,
        900.0,
        "Acciaio armonico da molla per impieghi generali.",
    ),
    (
        "AISI302",
        "AISI 302",
        193000.0,
        77000.0,
        450.0,
        800.0,
        "Acciaio inox austenitico, buona resistenza alla corrosione.",
    ),
    (
        "50CRV4",
        "50CrV4",
        206000.0,
        81000.0,
        650.0,
        1100.0,
        "Acciaio legato Cr-V ad alta resistenza.",
    ),
    (
        "17-7PH",
        "17-7PH",
        200000.0,
        77000.0,
        700.0,
        1200.0,
        "Inox induribile per precipitazione.",
    ),
    (
        "CUSN6",
        "Bronzo CuSn6",
        110000.0,
        42000.0,
        250.0,
        420.0,
        "Bronzo elastico per ambienti corrosivi e conduttivita.",
    ),
    (
        "EN10270-SH",
        "EN 10270-1 SH",
        206000.0,
        81500.0,
        620.0,
        1020.0,
        "Acciaio armonico per molle ad alta resistenza.",
    ),
    (
        "EN10270-DH",
        "EN 10270-1 DH",
        206000.0,
        81500.0,
        700.0,
        1180.0,
        "Acciaio armonico per molle molto sollecitate.",
    ),
    (
        "EN10270-2",
        "EN 10270-2 CrSi",
        206000.0,
        81000.0,
        700.0,
        1200.0,
        "Acciaio legato CrSi per molle dinamiche.",
    ),
    (
        "EN10270-3-4310",
        "EN 10270-3 1.4310",
        193000.0,
        77000.0,
        480.0,
        850.0,
        "Acciaio inox per molle in ambienti corrosivi.",
    ),
    (
        "EN10270-3-4568",
        "EN 10270-3 1.4568",
        200000.0,
        77000.0,
        680.0,
        1150.0,
        "Inox induribile per precipitazione (17-7PH).",
    ),
    (
        "55CR3",
        "55Cr3",
        206000.0,
        81000.0,
        620.0,
        1050.0,
        "Acciaio Si-Cr per molle meccaniche.",
    ),
    (
        "60SICR7",
        "60SiCr7",
        206000.0,
        81000.0,
        700.0,
        1200.0,
        "Acciaio Si-Cr ad alta resistenza a fatica.",
    ),
    (
        "51CRV4",
        "51CrV4",
        206000.0,
        81000.0,
        660.0,
        1120.0,
        "Acciaio CrV per molle ad elevata tenacita.",
    ),
    (
        "AISI301",
        "AISI 301",
        193000.0,
        77000.0,
        470.0,
        820.0,
        "Inox austenitico per nastri e molle sottili.",
    ),
    (
        "AISI316",
        "AISI 316",
        193000.0,
        77000.0,
        430.0,
        760.0,
        "Inox austenitico con migliore resistenza alla corrosione.",
    ),
    (
        "INCONEL-X750",
        "Inconel X-750",
        210000.0,
        80000.0,
        780.0,
        1300.0,
        "Superlega per alte temperature e fatica elevata.",
    ),
    (
        "NIMONIC90",
        "Nimonic 90",
        213000.0,
        81000.0,
        820.0,
        1380.0,
        "Superlega nichel-cromo-cobalto per alte temperature.",
    ),
    (
        "CUBE2",
        "Rame-Berillio CuBe2",
        131000.0,
        50000.0,
        520.0,
        900.0,
        "Lega rame ad alta resilienza e conducibilita.",
    ),
    (
        "CUSN8",
        "Bronzo CuSn8",
        115000.0,
        44000.0,
        280.0,
        470.0,
        "Bronzo fosforoso per molle e lamelle elastiche.",
    ),
    (
        "C75S",
        "C75S",
        206000.0,
        81000.0,
        560.0,
        950.0,
        "Acciaio al carbonio per molle piane e nastri.",
    ),
    (
        "AISI420",
        "AISI 420",
        200000.0,
        77000.0,
        520.0,
        900.0,
        "Inox martensitico per molle con buona durezza.",
    ),
    (
        "TI-GR5",
        "Titanio Ti-6Al-4V (Grado 5)",
        114000.0,
        44000.0,
        480.0,
        900.0,
        "Lega di titanio leggera con ottima resistenza specifica.",
    ),
    (
        "X12CRNISI177",
        "X12CrNiSi17-7",
        200000.0,
        77000.0,
        680.0,
        1150.0,
        "Acciaio inox martensitico-austenitico per molle.",
    ),
)


_DISC_SERIES: tuple[tuple[float, float, float, str], ...] = (
    # Compatibilita con le dimensioni storiche gia presenti nel progetto.
    (50.0, 25.0, 2.0, "Legacy"),
    (63.0, 31.5, 2.5, "Legacy"),
    (80.0, 41.0, 3.0, "Legacy"),
    (100.0, 51.0, 4.0, "Legacy"),
    (125.0, 64.0, 5.0, "Legacy"),
    # Serie estesa tipo DIN 2093 (gruppi 1/2/3, valori nominali tipici).
    (8.0, 4.2, 0.25, "G1"),
    (10.0, 5.2, 0.30, "G1"),
    (12.5, 6.2, 0.40, "G1"),
    (14.0, 7.2, 0.40, "G1"),
    (16.0, 8.2, 0.50, "G1"),
    (18.0, 9.2, 0.60, "G1"),
    (20.0, 10.2, 0.60, "G1"),
    (22.4, 11.2, 0.70, "G1"),
    (25.0, 12.2, 0.80, "G1"),
    (28.0, 14.2, 0.90, "G1"),
    (31.5, 16.3, 1.00, "G1"),
    (35.5, 18.3, 1.25, "G1"),
    (40.0, 20.4, 1.25, "G1"),
    (45.0, 22.4, 1.50, "G1"),
    (50.0, 25.4, 1.50, "G1"),
    (56.0, 28.4, 1.75, "G1"),
    (63.0, 31.5, 2.00, "G1"),
    (71.0, 35.5, 2.25, "G1"),
    (80.0, 41.0, 2.50, "G1"),
    (90.0, 46.0, 3.00, "G1"),
    (100.0, 51.0, 3.00, "G1"),
    (112.0, 57.0, 3.50, "G1"),
    (125.0, 64.0, 4.00, "G1"),
    (40.0, 20.4, 2.00, "G2"),
    (45.0, 22.4, 2.20, "G2"),
    (50.0, 25.4, 2.50, "G2"),
    (56.0, 28.4, 2.80, "G2"),
    (63.0, 31.5, 3.00, "G2"),
    (71.0, 35.5, 3.50, "G2"),
    (80.0, 41.0, 4.00, "G2"),
    (90.0, 46.0, 4.50, "G2"),
    (100.0, 51.0, 5.00, "G2"),
    (112.0, 57.0, 5.50, "G2"),
    (125.0, 64.0, 6.00, "G2"),
    (140.0, 72.0, 6.50, "G2"),
    (160.0, 82.0, 7.00, "G2"),
    (180.0, 92.0, 8.00, "G2"),
    (200.0, 102.0, 9.00, "G2"),
    (224.0, 115.0, 10.00, "G2"),
    (250.0, 127.0, 11.00, "G2"),
    (100.0, 51.0, 6.00, "G3"),
    (112.0, 57.0, 6.50, "G3"),
    (125.0, 64.0, 8.00, "G3"),
    (140.0, 72.0, 8.00, "G3"),
    (160.0, 82.0, 9.00, "G3"),
    (180.0, 92.0, 10.00, "G3"),
    (200.0, 102.0, 11.00, "G3"),
    (224.0, 115.0, 12.50, "G3"),
    (250.0, 127.0, 14.00, "G3"),
    (280.0, 143.0, 16.00, "G3"),
    (315.0, 162.0, 18.00, "G3"),
    (355.0, 183.0, 20.00, "G3"),
    (400.0, 206.0, 22.00, "G3"),
    (450.0, 232.0, 25.00, "G3"),
    (500.0, 257.0, 28.00, "G3"),
    (560.0, 290.0, 31.00, "G3"),
    (630.0, 326.0, 34.00, "G3"),
    (710.0, 368.0, 38.00, "G3"),
    (800.0, 420.0, 42.00, "G3"),
)


def _fmt_dim(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _build_default_disc_springs() -> tuple[tuple[str, str, float, float, float, float, str], ...]:
    rows: list[tuple[str, str, float, float, float, float, str]] = []
    for do_mm, di_mm, t_mm, series in _DISC_SERIES:
        do_s = _fmt_dim(do_mm)
        di_s = _fmt_dim(di_mm)
        t_s = _fmt_dim(t_mm)
        code = f"DIN2093-{do_s}x{di_s}x{t_s}"
        name = f"DIN 2093 {do_s}x{di_s}x{t_s}"
        h0_mm = round(t_mm * 0.60, 3)
        rows.append(
            (
                code,
                name,
                do_mm,
                di_mm,
                t_mm,
                h0_mm,
                f"Molla a tazza standard serie {series} (h0 nominale circa 0.6*t).",
            )
        )
    return tuple(rows)


DEFAULT_DISC_SPRINGS: tuple[tuple[str, str, float, float, float, float, str], ...] = _build_default_disc_springs()


class SpringMaterialsDB:
    def __init__(self, db_path: str | None = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_db = os.path.join(base_dir, "database", "spring_materials.db")
        self.db_path = db_path or default_db

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def ensure_seeded(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS spring_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    e_mpa REAL NOT NULL,
                    g_mpa REAL NOT NULL,
                    tau_amm_mpa REAL NOT NULL,
                    sigma_amm_mpa REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS disc_springs_standard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    do_mm REAL NOT NULL,
                    di_mm REAL NOT NULL,
                    t_mm REAL NOT NULL,
                    h0_mm REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            for row in DEFAULT_MATERIALS:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO spring_materials
                    (code, name, e_mpa, g_mpa, tau_amm_mpa, sigma_amm_mpa, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            for row in DEFAULT_DISC_SPRINGS:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO disc_springs_standard
                    (code, name, do_mm, di_mm, t_mm, h0_mm, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            conn.commit()

    def list_all(self) -> list[SpringMaterial]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, e_mpa, g_mpa, tau_amm_mpa, sigma_amm_mpa, notes
                FROM spring_materials
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        return [
            SpringMaterial(
                id=int(r[0]),
                code=str(r[1]),
                name=str(r[2]),
                e_mpa=float(r[3]),
                g_mpa=float(r[4]),
                tau_amm_mpa=float(r[5]),
                sigma_amm_mpa=float(r[6]),
                notes=str(r[7] or ""),
            )
            for r in rows
        ]

    def list_names(self) -> list[str]:
        return [m.name for m in self.list_all()]

    def get_by_name(self, name: str) -> SpringMaterial | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, e_mpa, g_mpa, tau_amm_mpa, sigma_amm_mpa, notes
                FROM spring_materials
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return SpringMaterial(
            id=int(row[0]),
            code=str(row[1]),
            name=str(row[2]),
            e_mpa=float(row[3]),
            g_mpa=float(row[4]),
            tau_amm_mpa=float(row[5]),
            sigma_amm_mpa=float(row[6]),
            notes=str(row[7] or ""),
        )

    def list_disc_springs(self) -> list[DiscSpringStandard]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, do_mm, di_mm, t_mm, h0_mm, notes
                FROM disc_springs_standard
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        return [
            DiscSpringStandard(
                id=int(r[0]),
                code=str(r[1]),
                name=str(r[2]),
                do_mm=float(r[3]),
                di_mm=float(r[4]),
                t_mm=float(r[5]),
                h0_mm=float(r[6]),
                notes=str(r[7] or ""),
            )
            for r in rows
        ]

    def list_disc_spring_names(self) -> list[str]:
        return [s.name for s in self.list_disc_springs()]

    def get_disc_spring_by_name(self, name: str) -> DiscSpringStandard | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, do_mm, di_mm, t_mm, h0_mm, notes
                FROM disc_springs_standard
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return DiscSpringStandard(
            id=int(row[0]),
            code=str(row[1]),
            name=str(row[2]),
            do_mm=float(row[3]),
            di_mm=float(row[4]),
            t_mm=float(row[5]),
            h0_mm=float(row[6]),
            notes=str(row[7] or ""),
        )
