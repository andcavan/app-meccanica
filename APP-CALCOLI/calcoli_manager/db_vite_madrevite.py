from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ScrewThreadStandard:
    id: int
    code: str
    family: str
    name: str
    d_mm: float
    p_mm: float
    d2_mm: float
    d3_mm: float
    d1_mm: float
    flank_angle_deg: float
    notes: str


@dataclass(frozen=True)
class ScrewNutMaterial:
    id: int
    code: str
    name: str
    sigma_amm_mpa: float
    tau_amm_mpa: float
    notes: str


_ISO_M_COARSE: tuple[tuple[float, float], ...] = (
    (1.0, 0.25),
    (1.2, 0.25),
    (1.4, 0.3),
    (1.6, 0.35),
    (1.8, 0.35),
    (2.0, 0.4),
    (2.5, 0.45),
    (3.0, 0.5),
    (3.5, 0.6),
    (4.0, 0.7),
    (5.0, 0.8),
    (6.0, 1.0),
    (7.0, 1.0),
    (8.0, 1.25),
    (10.0, 1.5),
    (12.0, 1.75),
    (14.0, 2.0),
    (16.0, 2.0),
    (18.0, 2.5),
    (20.0, 2.5),
    (22.0, 2.5),
    (24.0, 3.0),
    (27.0, 3.0),
    (30.0, 3.5),
    (33.0, 3.5),
    (36.0, 4.0),
    (39.0, 4.0),
    (42.0, 4.5),
    (45.0, 4.5),
    (48.0, 5.0),
    (52.0, 5.0),
    (56.0, 5.5),
    (60.0, 5.5),
    (64.0, 6.0),
)

_ISO_M_FINE: tuple[tuple[float, float], ...] = (
    (8.0, 1.0),
    (10.0, 1.25),
    (10.0, 1.0),
    (12.0, 1.5),
    (12.0, 1.25),
    (14.0, 1.5),
    (14.0, 1.25),
    (16.0, 1.5),
    (16.0, 1.0),
    (18.0, 2.0),
    (18.0, 1.5),
    (20.0, 2.0),
    (20.0, 1.5),
    (22.0, 2.0),
    (24.0, 2.0),
    (24.0, 1.5),
    (27.0, 2.0),
    (27.0, 1.5),
    (30.0, 2.0),
    (30.0, 1.5),
    (33.0, 2.0),
    (33.0, 1.5),
    (36.0, 3.0),
    (36.0, 2.0),
    (39.0, 3.0),
    (39.0, 2.0),
    (42.0, 3.0),
    (42.0, 2.0),
    (45.0, 3.0),
    (45.0, 2.0),
    (48.0, 3.0),
    (48.0, 2.0),
    (52.0, 4.0),
    (52.0, 3.0),
    (56.0, 4.0),
    (56.0, 3.0),
    (60.0, 4.0),
    (60.0, 3.0),
    (64.0, 4.0),
    (64.0, 3.0),
)

_TRAPEZOIDAL: tuple[tuple[float, float], ...] = (
    (8.0, 1.5),
    (9.0, 2.0),
    (10.0, 2.0),
    (11.0, 3.0),
    (12.0, 3.0),
    (14.0, 3.0),
    (16.0, 4.0),
    (18.0, 4.0),
    (20.0, 4.0),
    (22.0, 5.0),
    (24.0, 5.0),
    (26.0, 5.0),
    (28.0, 5.0),
    (30.0, 6.0),
    (32.0, 6.0),
    (36.0, 6.0),
    (40.0, 7.0),
    (44.0, 7.0),
    (48.0, 8.0),
    (52.0, 8.0),
    (56.0, 8.0),
    (60.0, 9.0),
    (70.0, 10.0),
    (80.0, 10.0),
    (90.0, 12.0),
    (100.0, 12.0),
)


def _fmt_dim(value: float) -> str:
    txt = f"{value:.3f}".rstrip("0").rstrip(".")
    return txt


def _iso_m_dims(d_mm: float, p_mm: float) -> tuple[float, float, float]:
    d2 = d_mm - (0.64952 * p_mm)
    d3 = d_mm - (1.22687 * p_mm)
    d1 = d_mm - (1.08253 * p_mm)
    return d2, d3, d1


def _tr_dims(d_mm: float, p_mm: float) -> tuple[float, float, float]:
    d2 = d_mm - (0.5 * p_mm)
    d3 = d_mm - p_mm
    d1 = d_mm - (0.5 * p_mm)
    return d2, d3, d1


def _build_default_thread_standards() -> tuple[tuple[str, str, str, float, float, float, float, float, float, str], ...]:
    rows: list[tuple[str, str, str, float, float, float, float, float, float, str]] = []
    seen_codes: set[str] = set()

    def _append_row(
        family: str,
        d_mm: float,
        p_mm: float,
        flank_angle_deg: float,
        notes: str,
        dim_fn,
        code_prefix: str,
        name_prefix: str,
    ) -> None:
        code = f"{code_prefix}{_fmt_dim(d_mm)}x{_fmt_dim(p_mm)}"
        if code in seen_codes:
            return
        d2_mm, d3_mm, d1_mm = dim_fn(d_mm, p_mm)
        rows.append(
            (
                code,
                family,
                f"{name_prefix} {code}",
                d_mm,
                p_mm,
                round(d2_mm, 4),
                round(d3_mm, 4),
                round(d1_mm, 4),
                flank_angle_deg,
                notes,
            )
        )
        seen_codes.add(code)

    for d_mm, p_mm in _ISO_M_COARSE:
        _append_row(
            family="ISO M",
            d_mm=d_mm,
            p_mm=p_mm,
            flank_angle_deg=60.0,
            notes="Metrica ISO passo grosso.",
            dim_fn=_iso_m_dims,
            code_prefix="M",
            name_prefix="ISO M",
        )

    for d_mm, p_mm in _ISO_M_FINE:
        _append_row(
            family="ISO M fine",
            d_mm=d_mm,
            p_mm=p_mm,
            flank_angle_deg=60.0,
            notes="Metrica ISO passo fine.",
            dim_fn=_iso_m_dims,
            code_prefix="M",
            name_prefix="ISO M fine",
        )

    for d_mm, p_mm in _TRAPEZOIDAL:
        _append_row(
            family="Trapezoidale",
            d_mm=d_mm,
            p_mm=p_mm,
            flank_angle_deg=30.0,
            notes="Filettatura trapezoidale metrica.",
            dim_fn=_tr_dims,
            code_prefix="Tr",
            name_prefix="TR",
        )

    return tuple(rows)


DEFAULT_THREAD_STANDARDS: tuple[tuple[str, str, str, float, float, float, float, float, float, str], ...] = (
    _build_default_thread_standards()
)


DEFAULT_SCREW_NUT_MATERIALS: tuple[tuple[str, str, float, float, str], ...] = (
    ("C45", "Acciaio C45 bonificato", 240.0, 140.0, "Uso generale per viti di potenza."),
    ("42CRMO4", "Acciaio 42CrMo4 bonificato", 360.0, 210.0, "Viti ad alta resistenza."),
    ("AISI304", "AISI 304", 170.0, 100.0, "Acciaio inox per ambienti corrosivi."),
    ("CUSRONZO", "Bronzo CuSn12", 95.0, 55.0, "Tipico materiale madrevite."),
    ("GJL250", "Ghisa EN-GJL-250", 85.0, 50.0, "Madrevite per carichi moderati."),
)


class ScrewNutDB:
    def __init__(self, db_path: str | None = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_db = os.path.join(base_dir, "database", "screw_nut_data.db")
        self.db_path = db_path or default_db

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def ensure_seeded(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS screw_thread_standards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    family TEXT NOT NULL,
                    name TEXT NOT NULL UNIQUE,
                    d_mm REAL NOT NULL,
                    p_mm REAL NOT NULL,
                    d2_mm REAL NOT NULL,
                    d3_mm REAL NOT NULL,
                    d1_mm REAL NOT NULL,
                    flank_angle_deg REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS screw_nut_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    sigma_amm_mpa REAL NOT NULL,
                    tau_amm_mpa REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            for row in DEFAULT_THREAD_STANDARDS:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO screw_thread_standards
                    (code, family, name, d_mm, p_mm, d2_mm, d3_mm, d1_mm, flank_angle_deg, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            for row in DEFAULT_SCREW_NUT_MATERIALS:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO screw_nut_materials
                    (code, name, sigma_amm_mpa, tau_amm_mpa, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    row,
                )
            conn.commit()

    def list_threads(self) -> list[ScrewThreadStandard]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, family, name, d_mm, p_mm, d2_mm, d3_mm, d1_mm, flank_angle_deg, notes
                FROM screw_thread_standards
                ORDER BY family, d_mm, p_mm
                """
            )
            rows = cur.fetchall()
        return [
            ScrewThreadStandard(
                id=int(r[0]),
                code=str(r[1]),
                family=str(r[2]),
                name=str(r[3]),
                d_mm=float(r[4]),
                p_mm=float(r[5]),
                d2_mm=float(r[6]),
                d3_mm=float(r[7]),
                d1_mm=float(r[8]),
                flank_angle_deg=float(r[9]),
                notes=str(r[10] or ""),
            )
            for r in rows
        ]

    def list_thread_names(self) -> list[str]:
        return [t.name for t in self.list_threads()]

    def get_thread_by_name(self, name: str) -> ScrewThreadStandard | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, family, name, d_mm, p_mm, d2_mm, d3_mm, d1_mm, flank_angle_deg, notes
                FROM screw_thread_standards
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return ScrewThreadStandard(
            id=int(row[0]),
            code=str(row[1]),
            family=str(row[2]),
            name=str(row[3]),
            d_mm=float(row[4]),
            p_mm=float(row[5]),
            d2_mm=float(row[6]),
            d3_mm=float(row[7]),
            d1_mm=float(row[8]),
            flank_angle_deg=float(row[9]),
            notes=str(row[10] or ""),
        )

    def list_materials(self) -> list[ScrewNutMaterial]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, sigma_amm_mpa, tau_amm_mpa, notes
                FROM screw_nut_materials
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        return [
            ScrewNutMaterial(
                id=int(r[0]),
                code=str(r[1]),
                name=str(r[2]),
                sigma_amm_mpa=float(r[3]),
                tau_amm_mpa=float(r[4]),
                notes=str(r[5] or ""),
            )
            for r in rows
        ]

    def list_material_names(self) -> list[str]:
        return [m.name for m in self.list_materials()]

    def get_material_by_name(self, name: str) -> ScrewNutMaterial | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, sigma_amm_mpa, tau_amm_mpa, notes
                FROM screw_nut_materials
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return ScrewNutMaterial(
            id=int(row[0]),
            code=str(row[1]),
            name=str(row[2]),
            sigma_amm_mpa=float(row[3]),
            tau_amm_mpa=float(row[4]),
            notes=str(row[5] or ""),
        )
