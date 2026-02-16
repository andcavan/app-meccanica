from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class BeamMaterial:
    id: int
    code: str
    name: str
    e_mpa: float
    g_mpa: float
    sigma_amm_mpa: float
    tau_amm_mpa: float
    notes: str


@dataclass(frozen=True)
class BeamSectionStandard:
    id: int
    code: str
    name: str
    section_type: str
    h_mm: float
    b_mm: float
    tw_mm: float
    tf_mm: float
    area_mm2: float
    ix_mm4: float
    wx_mm3: float
    notes: str


DEFAULT_BEAM_MATERIALS: tuple[tuple[str, str, float, float, float, float, str], ...] = (
    (
        "S235JR",
        "Acciaio S235JR",
        210000.0,
        81000.0,
        160.0,
        95.0,
        "Acciaio strutturale per carpenteria generale.",
    ),
    (
        "S275JR",
        "Acciaio S275JR",
        210000.0,
        81000.0,
        180.0,
        105.0,
        "Acciaio strutturale intermedio.",
    ),
    (
        "S355JR",
        "Acciaio S355JR",
        210000.0,
        81000.0,
        230.0,
        135.0,
        "Acciaio strutturale a maggiore resistenza.",
    ),
    (
        "C45",
        "Acciaio C45",
        210000.0,
        81000.0,
        260.0,
        150.0,
        "Acciaio da bonifica per alberi e componenti meccanici.",
    ),
    (
        "42CRMO4",
        "Acciaio 42CrMo4",
        210000.0,
        81000.0,
        550.0,
        320.0,
        "Acciaio legato da bonifica ad alta resistenza.",
    ),
    (
        "AISI304",
        "AISI 304",
        193000.0,
        77000.0,
        170.0,
        100.0,
        "Acciaio inox austenitico per ambienti corrosivi.",
    ),
    (
        "AISI316",
        "AISI 316",
        193000.0,
        77000.0,
        175.0,
        105.0,
        "Acciaio inox austenitico con molibdeno.",
    ),
    (
        "EN-AW6060-T6",
        "Alluminio EN AW-6060 T6",
        69000.0,
        26000.0,
        100.0,
        60.0,
        "Lega leggera per profili estrusi standard.",
    ),
    (
        "EN-AW6082-T6",
        "Alluminio EN AW-6082 T6",
        70000.0,
        26000.0,
        160.0,
        95.0,
        "Lega leggera con buon compromesso peso/resistenza.",
    ),
    (
        "EN-AW7075-T6",
        "Alluminio EN AW-7075 T6",
        71000.0,
        27000.0,
        330.0,
        190.0,
        "Lega leggera ad alta resistenza (Ergal).",
    ),
    (
        "GJL-250",
        "Ghisa Grigia GJL-250",
        105000.0,
        40000.0,
        80.0,
        50.0,
        "Ghisa lamellare per basamenti e supporti.",
    ),
    (
        "GJS-400",
        "Ghisa Sferoidale GJS-400",
        169000.0,
        65000.0,
        160.0,
        95.0,
        "Ghisa sferoidale con buona duttilità.",
    ),
    (
        "TI-GR5",
        "Titanio Grado 5",
        114000.0,
        44000.0,
        550.0,
        320.0,
        "Lega di titanio Ti-6Al-4V ad alte prestazioni.",
    ),
)


DEFAULT_BEAM_SECTIONS_STD: tuple[tuple[str, str, str, float, float, float, float, float, float, float, str], ...] = (
    (
        "IPE80",
        "IPE 80",
        "IPE",
        80.0,
        46.0,
        3.8,
        5.2,
        764.0,
        8_010_000.0,
        20_000.0,
        "Valori indicativi asse forte x.",
    ),
    (
        "IPE100",
        "IPE 100",
        "IPE",
        100.0,
        55.0,
        4.1,
        5.7,
        1_030.0,
        17_100_000.0,
        34_200.0,
        "Valori indicativi asse forte x.",
    ),
    (
        "IPE120",
        "IPE 120",
        "IPE",
        120.0,
        64.0,
        4.4,
        6.3,
        1_320.0,
        31_700_000.0,
        52_800.0,
        "Valori indicativi asse forte x.",
    ),
    (
        "IPE140",
        "IPE 140",
        "IPE",
        140.0,
        73.0,
        4.7,
        6.9,
        1_640.0,
        54_100_000.0,
        77_300.0,
        "Valori indicativi asse forte x.",
    ),
    (
        "IPE160",
        "IPE 160",
        "IPE",
        160.0,
        82.0,
        5.0,
        7.4,
        2_010.0,
        86_900_000.0,
        108_600.0,
        "Valori indicativi asse forte x.",
    ),
)


class BeamMaterialsDB:
    def __init__(self, db_path: str | None = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_db = os.path.join(base_dir, "database", "beam_materials.db")
        self.db_path = db_path or default_db

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def ensure_seeded(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS beam_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    e_mpa REAL NOT NULL,
                    g_mpa REAL NOT NULL,
                    sigma_amm_mpa REAL NOT NULL,
                    tau_amm_mpa REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS beam_sections_std (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    section_type TEXT NOT NULL,
                    h_mm REAL NOT NULL,
                    b_mm REAL NOT NULL,
                    tw_mm REAL NOT NULL,
                    tf_mm REAL NOT NULL,
                    area_mm2 REAL NOT NULL,
                    ix_mm4 REAL NOT NULL,
                    wx_mm3 REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            for row in DEFAULT_BEAM_MATERIALS:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO beam_materials
                    (code, name, e_mpa, g_mpa, sigma_amm_mpa, tau_amm_mpa, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            for row in DEFAULT_BEAM_SECTIONS_STD:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO beam_sections_std
                    (code, name, section_type, h_mm, b_mm, tw_mm, tf_mm, area_mm2, ix_mm4, wx_mm3, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            conn.commit()

    def list_all(self) -> list[BeamMaterial]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, e_mpa, g_mpa, sigma_amm_mpa, tau_amm_mpa, notes
                FROM beam_materials
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        return [
            BeamMaterial(
                id=int(r[0]),
                code=str(r[1]),
                name=str(r[2]),
                e_mpa=float(r[3]),
                g_mpa=float(r[4]),
                sigma_amm_mpa=float(r[5]),
                tau_amm_mpa=float(r[6]),
                notes=str(r[7] or ""),
            )
            for r in rows
        ]

    def list_names(self) -> list[str]:
        return [m.name for m in self.list_all()]

    def get_by_name(self, name: str) -> BeamMaterial | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, e_mpa, g_mpa, sigma_amm_mpa, tau_amm_mpa, notes
                FROM beam_materials
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return BeamMaterial(
            id=int(row[0]),
            code=str(row[1]),
            name=str(row[2]),
            e_mpa=float(row[3]),
            g_mpa=float(row[4]),
            sigma_amm_mpa=float(row[5]),
            tau_amm_mpa=float(row[6]),
            notes=str(row[7] or ""),
        )

    def list_sections_std(self) -> list[BeamSectionStandard]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, section_type, h_mm, b_mm, tw_mm, tf_mm, area_mm2, ix_mm4, wx_mm3, notes
                FROM beam_sections_std
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        return [
            BeamSectionStandard(
                id=int(r[0]),
                code=str(r[1]),
                name=str(r[2]),
                section_type=str(r[3]),
                h_mm=float(r[4]),
                b_mm=float(r[5]),
                tw_mm=float(r[6]),
                tf_mm=float(r[7]),
                area_mm2=float(r[8]),
                ix_mm4=float(r[9]),
                wx_mm3=float(r[10]),
                notes=str(r[11] or ""),
            )
            for r in rows
        ]

    def list_section_names(self) -> list[str]:
        return [s.name for s in self.list_sections_std()]

    def get_section_by_name(self, name: str) -> BeamSectionStandard | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, section_type, h_mm, b_mm, tw_mm, tf_mm, area_mm2, ix_mm4, wx_mm3, notes
                FROM beam_sections_std
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return BeamSectionStandard(
            id=int(row[0]),
            code=str(row[1]),
            name=str(row[2]),
            section_type=str(row[3]),
            h_mm=float(row[4]),
            b_mm=float(row[5]),
            tw_mm=float(row[6]),
            tf_mm=float(row[7]),
            area_mm2=float(row[8]),
            ix_mm4=float(row[9]),
            wx_mm3=float(row[10]),
            notes=str(row[11] or ""),
        )
