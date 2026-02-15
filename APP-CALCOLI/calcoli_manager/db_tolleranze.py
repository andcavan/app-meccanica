from __future__ import annotations

import math
import os
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ToleranceMaterial:
    id: int
    code: str
    name: str
    category: str
    alpha_um_mk: float
    notes: str


@dataclass(frozen=True)
class IsoToleranceZone:
    id: int
    component: str
    code: str
    d_min_mm: float
    d_max_mm: float
    lower_dev_um: float
    upper_dev_um: float
    notes: str


DEFAULT_TOL_MATERIALS: tuple[tuple[str, str, str, float, str], ...] = (
    ("S235JR", "Acciaio S235JR", "ACCIAI", 12.0, "Acciaio strutturale al carbonio."),
    ("C45", "Acciaio C45", "ACCIAI", 11.5, "Acciaio da bonifica per alberi."),
    ("42CRMO4", "Acciaio 42CrMo4", "ACCIAI", 11.7, "Acciaio legato per componenti meccanici."),
    ("16MNCR5", "Acciaio 16MnCr5", "ACCIAI", 11.4, "Acciaio da cementazione."),
    ("AISI304", "AISI 304", "ACCIAI INOX", 17.3, "Inox austenitico."),
    ("AISI316L", "AISI 316L", "ACCIAI INOX", 16.0, "Inox austenitico per corrosione severa."),
    ("AISI420", "AISI 420", "ACCIAI INOX", 10.4, "Inox martensitico."),
    ("EN-AW6061", "Alluminio EN AW-6061", "ALLUMINI", 23.6, "Lega leggera uso generale."),
    ("EN-AW6082", "Alluminio EN AW-6082", "ALLUMINI", 23.4, "Lega leggera strutturale."),
    ("EN-AW7075", "Alluminio EN AW-7075", "ALLUMINI", 23.5, "Lega alta resistenza."),
    ("CW614N", "Ottone CW614N (OT58)", "OTTONI", 19.0, "Ottone per lavorazioni meccaniche."),
    ("CW617N", "Ottone CW617N", "OTTONI", 20.0, "Ottone stampato."),
    ("CUSN8", "Bronzo CuSn8", "BRONZI", 17.5, "Bronzo allo stagno."),
    ("CUSN12", "Bronzo CuSn12", "BRONZI", 17.0, "Bronzo antiusura."),
    ("CUAL10NI5FE4", "Bronzo CuAl10Ni5Fe4", "BRONZI", 16.5, "Bronzo all'alluminio."),
    ("POM-C", "POM-C", "MATERIE PLASTICHE", 110.0, "Poliossimetilene."),
    ("PA6", "PA6", "MATERIE PLASTICHE", 90.0, "Poliammide 6."),
    ("PA66", "PA66", "MATERIE PLASTICHE", 80.0, "Poliammide 66."),
    ("PTFE", "PTFE", "MATERIE PLASTICHE", 130.0, "Politetrafluoroetilene."),
    ("PEEK", "PEEK", "MATERIE PLASTICHE", 47.0, "Polimero tecnico alte prestazioni."),
)

_SIZE_BANDS: tuple[tuple[float, float], ...] = (
    (0.0, 1.0),
    (1.0, 3.0),
    (3.0, 6.0),
    (6.0, 10.0),
    (10.0, 18.0),
    (18.0, 30.0),
    (30.0, 50.0),
    (50.0, 80.0),
    (80.0, 120.0),
    (120.0, 180.0),
    (180.0, 250.0),
    (250.0, 315.0),
    (315.0, 400.0),
    (400.0, 500.0),
    (500.0, 630.0),
    (630.0, 800.0),
    (800.0, 1000.0),
    (1000.0, 1250.0),
    (1250.0, 1600.0),
    (1600.0, 2000.0),
    (2000.0, 2500.0),
    (2500.0, 3150.0),
)

_IT_LABELS: tuple[str, ...] = ("01", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18")

_IT_MULTIPLIERS: dict[int, float] = {
    5: 7.0,
    6: 10.0,
    7: 16.0,
    8: 25.0,
    9: 40.0,
    10: 64.0,
    11: 100.0,
    12: 160.0,
    13: 250.0,
    14: 400.0,
    15: 640.0,
    16: 1000.0,
    17: 1600.0,
    18: 2500.0,
}

_SHAFT_LETTERS: tuple[str, ...] = (
    "a",
    "b",
    "c",
    "cd",
    "d",
    "e",
    "ef",
    "f",
    "fg",
    "g",
    "h",
    "js",
    "j",
    "k",
    "m",
    "n",
    "p",
    "r",
    "s",
    "t",
    "u",
    "v",
    "x",
    "y",
    "z",
    "za",
    "zb",
    "zc",
)

_HOLE_LETTERS: tuple[str, ...] = tuple(letter.upper() for letter in _SHAFT_LETTERS)

_SHAFT_DEVIATION_FACTORS: dict[str, float] = {
    "a": -85.0,
    "b": -63.0,
    "c": -45.0,
    "cd": -39.0,
    "d": -34.0,
    "e": -23.0,
    "ef": -16.0,
    "f": -10.0,
    "fg": -7.0,
    "g": -5.0,
    "h": 0.0,
    "j": 3.0,
    "k": 4.0,
    "m": 10.0,
    "n": 14.0,
    "p": 24.0,
    "r": 34.0,
    "s": 45.0,
    "t": 56.0,
    "u": 72.0,
    "v": 90.0,
    "x": 110.0,
    "y": 140.0,
    "z": 180.0,
    "za": 220.0,
    "zb": 280.0,
    "zc": 360.0,
}


def _iso_mean_diameter(d_min: float, d_max: float) -> float:
    if d_min <= 0:
        return max(0.5, d_max / 2.0)
    return math.sqrt(d_min * d_max)


def _iso_tolerance_unit_i_um(d_mean: float) -> float:
    if d_mean <= 500.0:
        return 0.45 * (d_mean ** (1.0 / 3.0)) + (0.001 * d_mean)
    return (0.004 * d_mean) + 2.1


def _iso_it_um(d_mean: float, it_label: str) -> float:
    if it_label == "01":
        return 0.3 + (0.008 * d_mean)
    if it_label == "0":
        return 0.5 + (0.012 * d_mean)
    grade = int(it_label)
    if grade == 1:
        return 0.8 + (0.020 * d_mean)
    if grade == 2:
        return 1.2 + (0.030 * d_mean)
    if grade == 3:
        return 2.0 + (0.048 * d_mean)
    if grade == 4:
        return 3.0 + (0.074 * d_mean)
    i = _iso_tolerance_unit_i_um(d_mean)
    mult = _IT_MULTIPLIERS.get(grade)
    if mult is None:
        raise ValueError(f"Classe IT non supportata: {it_label}")
    return i * mult


def _shaft_es_um(letter: str, d_mean: float) -> float:
    if letter == "js":
        return 0.0
    factor = _SHAFT_DEVIATION_FACTORS.get(letter)
    if factor is None:
        raise ValueError(f"Lettera albero non supportata: {letter}")
    return factor * _iso_tolerance_unit_i_um(d_mean)


def _iso_code_sort_key(code: str) -> tuple[str, int]:
    txt = code.strip()
    i = len(txt) - 1
    while i >= 0 and txt[i].isdigit():
        i -= 1
    letter = txt[: i + 1]
    grade_label = txt[i + 1 :]
    try:
        grade_pos = _IT_LABELS.index(grade_label)
    except ValueError:
        grade_pos = len(_IT_LABELS) + 99
    return letter, grade_pos


def _split_iso_code(code: str) -> tuple[str, str]:
    txt = code.strip()
    if not txt:
        return "", ""
    i = len(txt) - 1
    while i >= 0 and txt[i].isdigit():
        i -= 1
    letter = txt[: i + 1]
    grade = txt[i + 1 :]
    return letter, grade


def _build_default_iso_zones() -> tuple[tuple[str, str, float, float, float, float, str], ...]:
    rows: list[tuple[str, str, float, float, float, float, str]] = []

    for d_min, d_max in _SIZE_BANDS:
        d_mean = _iso_mean_diameter(d_min, d_max)
        for it_label in _IT_LABELS:
            it_um = _iso_it_um(d_mean, it_label)

            for letter in _SHAFT_LETTERS:
                if letter == "js":
                    ei = -it_um / 2.0
                    es = it_um / 2.0
                else:
                    es = _shaft_es_um(letter, d_mean)
                    ei = es - it_um
                rows.append(
                    (
                        "SHAFT",
                        f"{letter}{it_label}",
                        d_min,
                        d_max,
                        ei,
                        es,
                        "Zona albero ISO generata (valori in um).",
                    )
                )

            for letter in _HOLE_LETTERS:
                low = letter.lower()
                if low == "h":
                    ei = 0.0
                    es = it_um
                elif low == "js":
                    ei = -it_um / 2.0
                    es = it_um / 2.0
                else:
                    ei = -_shaft_es_um(low, d_mean)
                    es = ei + it_um
                rows.append(
                    (
                        "HOLE",
                        f"{letter}{it_label}",
                        d_min,
                        d_max,
                        ei,
                        es,
                        "Zona foro ISO generata (valori in um).",
                    )
                )
    return tuple(rows)


DEFAULT_ISO_ZONES = _build_default_iso_zones()


class ToleranceDB:
    def __init__(self, db_path: str | None = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_db = os.path.join(base_dir, "database", "tolerance_data.db")
        self.db_path = db_path or default_db

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def ensure_seeded(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fit_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    alpha_um_mk REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS iso_tolerance_zones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    code TEXT NOT NULL,
                    d_min_mm REAL NOT NULL,
                    d_max_mm REAL NOT NULL,
                    lower_dev_um REAL NOT NULL,
                    upper_dev_um REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    UNIQUE(component, code, d_min_mm, d_max_mm)
                )
                """
            )
            for row in DEFAULT_TOL_MATERIALS:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO fit_materials
                    (code, name, category, alpha_um_mk, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    row,
                )
            for row in DEFAULT_ISO_ZONES:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO iso_tolerance_zones
                    (component, code, d_min_mm, d_max_mm, lower_dev_um, upper_dev_um, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            conn.commit()

    def list_materials(self) -> list[ToleranceMaterial]:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, category, alpha_um_mk, notes
                FROM fit_materials
                ORDER BY category, name
                """
            )
            rows = cur.fetchall()
        return [
            ToleranceMaterial(
                id=int(r[0]),
                code=str(r[1]),
                name=str(r[2]),
                category=str(r[3]),
                alpha_um_mk=float(r[4]),
                notes=str(r[5] or ""),
            )
            for r in rows
        ]

    def list_material_names(self) -> list[str]:
        return [m.name for m in self.list_materials()]

    def get_material_by_name(self, name: str) -> ToleranceMaterial | None:
        self.ensure_seeded()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, category, alpha_um_mk, notes
                FROM fit_materials
                WHERE name=?
                """,
                (name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return ToleranceMaterial(
            id=int(row[0]),
            code=str(row[1]),
            name=str(row[2]),
            category=str(row[3]),
            alpha_um_mk=float(row[4]),
            notes=str(row[5] or ""),
        )

    def list_iso_codes(self, component: str) -> list[str]:
        self.ensure_seeded()
        comp = component.strip().upper()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT code
                FROM iso_tolerance_zones
                WHERE component=?
                ORDER BY code
                """,
                (comp,),
            )
            rows = cur.fetchall()
        codes = [str(r[0]) for r in rows]
        return sorted(codes, key=_iso_code_sort_key)

    def list_iso_positions(self, component: str) -> list[str]:
        codes = self.list_iso_codes(component)
        positions = { _split_iso_code(code)[0] for code in codes if _split_iso_code(code)[0] }
        return sorted(positions, key=lambda x: (x.upper(), len(x), x))

    def list_iso_grades(self, component: str) -> list[str]:
        codes = self.list_iso_codes(component)
        grades = { _split_iso_code(code)[1] for code in codes if _split_iso_code(code)[1] }
        return sorted(grades, key=lambda g: _IT_LABELS.index(g) if g in _IT_LABELS else len(_IT_LABELS) + 99)

    def get_iso_zone(self, component: str, code: str, nominal_d_mm: float) -> IsoToleranceZone | None:
        self.ensure_seeded()
        comp = component.strip().upper()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, component, code, d_min_mm, d_max_mm, lower_dev_um, upper_dev_um, notes
                FROM iso_tolerance_zones
                WHERE component=?
                  AND code=?
                  AND ? > d_min_mm
                  AND ? <= d_max_mm
                ORDER BY d_max_mm
                LIMIT 1
                """,
                (comp, code, nominal_d_mm, nominal_d_mm),
            )
            row = cur.fetchone()
        if not row:
            return None
        return IsoToleranceZone(
            id=int(row[0]),
            component=str(row[1]),
            code=str(row[2]),
            d_min_mm=float(row[3]),
            d_max_mm=float(row[4]),
            lower_dev_um=float(row[5]),
            upper_dev_um=float(row[6]),
            notes=str(row[7] or ""),
        )
