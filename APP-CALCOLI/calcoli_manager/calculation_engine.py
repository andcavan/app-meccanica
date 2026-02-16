from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Sequence

try:
    import customtkinter as ctk
except Exception as e:
    raise SystemExit(
        "Questa app usa 'customtkinter'. Installa con:\n\n"
        "  pip install -r requirements.txt\n\n"
        f"Dettagli import: {e}"
    )
from tkinter import messagebox

from .config import APP_NAME, APP_VERSION
from .db_molle import DiscSpringStandard, SpringMaterial, SpringMaterialsDB
from .db_tolleranze import IsoToleranceZone, ToleranceDB, ToleranceMaterial
from .db_travi import BeamMaterial, BeamMaterialsDB, BeamSectionStandard
from .db_vite_madrevite import ScrewNutDB, ScrewNutMaterial, ScrewThreadStandard
from .my_style_01.style import Palette, STYLE_NAME, apply_style

CalcRows = list[tuple[str, str]]
CalcValue = float | int | str | None
CalcFn = Callable[[dict[str, CalcValue]], CalcRows]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    default: str = ""
    unit: str = ""
    field_type: str = "float"  # float | int | choice | radio | float_optional
    choices: tuple[str, ...] = ()


def _as_float(raw: str, label: str) -> float:
    txt = (raw or "").strip().replace(",", ".")
    if not txt:
        raise ValueError(f"Compila {label}.")
    try:
        return float(txt)
    except Exception as exc:
        raise ValueError(f"{label}: valore numerico non valido.") from exc


def _as_int(raw: str, label: str) -> int:
    value = _as_float(raw, label)
    rounded = round(value)
    if abs(value - rounded) > 1e-9:
        raise ValueError(f"{label}: inserisci un intero.")
    return int(rounded)


def _fmt_number(value: float, digits: int = 4) -> str:
    if math.isnan(value) or math.isinf(value):
        return "-"
    abs_v = abs(value)
    if abs_v >= 1_000_000 or (0 < abs_v < 1e-4):
        txt = f"{value:.4e}"
    else:
        txt = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return txt.replace(".", ",")


def _v(value: float, unit: str = "", digits: int = 4) -> str:
    base = _fmt_number(value, digits=digits)
    return f"{base} {unit}".strip()


def _lighten_hex_color(hex_color, factor: float):
    if isinstance(hex_color, (tuple, list)):
        out = [_lighten_hex_color(c, factor) for c in hex_color]
        return tuple(out) if isinstance(hex_color, tuple) else out
    if not isinstance(hex_color, str):
        return hex_color
    color = hex_color.strip()
    if len(color) != 7 or not color.startswith("#"):
        return hex_color
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
    except Exception:
        return hex_color
    f = min(max(factor, 0.0), 1.0)
    r2 = int(r + ((255 - r) * f))
    g2 = int(g + ((255 - g) * f))
    b2 = int(b + ((255 - b) * f))
    return f"#{r2:02x}{g2:02x}{b2:02x}"


def _require_gt_zero(label: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{label} deve essere > 0.")


def _require_ge_zero(label: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{label} deve essere >= 0.")


SPRING_DB = SpringMaterialsDB()
BEAM_DB = BeamMaterialsDB()
TOL_DB = ToleranceDB()
SCREW_DB = ScrewNutDB()

SPRING_TERMINALS_COMPRESSION = (
    "APERTE",
    "CHIUSE",
    "CHIUSE E RETTIFICATE",
)

SPRING_TERMINALS_TRACTION = (
    "OCCHIELLI INGLESI",
    "OCCHIELLI TEDESCHI",
    "GANCI TEDESCHI",
)

SPRING_CALC_MODE_FORCE_FROM_DEF = "f1/f2 mm"
SPRING_CALC_MODE_FORCE_FROM_DEF_ANG = "f1/f2 °"
SPRING_CALC_MODE_DEF_FROM_FORCE = "F1/F2 N"
SPRING_MAT_FIELD_KEYS = ("mat_e", "mat_g", "mat_sigma_amm", "mat_tau_amm")
BEAM_MAT_FIELD_KEYS = ("matb_e", "matb_g", "matb_sigma_amm", "matb_tau_amm")
DISC_SPRING_SOURCE_DB = "DB STANDARD"
DISC_SPRING_SOURCE_CUSTOM = "PERSONALIZZATA"
BEAM_SECTION_ROUND = "TONDO"
BEAM_SECTION_TUBE = "TUBO"
BEAM_SECTION_RECT = "RETTANGOLARE"
BEAM_SECTION_RECT_TUBE = "TUBOLARE"
BEAM_SECTION_STD = "SEZIONE STD"
BEAM_SECTION_TYPES = (
    BEAM_SECTION_ROUND,
    BEAM_SECTION_TUBE,
    BEAM_SECTION_RECT,
    BEAM_SECTION_RECT_TUBE,
    BEAM_SECTION_STD,
)
BEAM_TORSION_SECTION_TYPES = (
    BEAM_SECTION_ROUND,
    BEAM_SECTION_TUBE,
    BEAM_SECTION_RECT,
    BEAM_SECTION_RECT_TUBE,
)
BEAM_SUPPORT_PINNED = ("APPOGGIATA", "INCERNIERATA")
BEAM_SUPPORT_FIXED = "INCASTRATA"
BEAM_SUPPORT_FREE = "LIBERA"
BEAM_SUPPORT_CHOICES = (
    "APPOGGIATA",
    "INCERNIERATA",
    "INCASTRATA",
    "LIBERA",
)
GEAR_X_MODE_BOTH = "Entrambi (x1=x2)"
GEAR_X_MODE_PINION = "Solo pignone (x2=0)"
GEAR_X_MODE_WHEEL = "Solo ruota (x1=0)"
GEAR_X_MODE_CHOICES = (
    GEAR_X_MODE_BOTH,
    GEAR_X_MODE_PINION,
    GEAR_X_MODE_WHEEL,
)
SCREW_VM_MODE_FORCE_FROM_TORQUE = "Da coppia a forza"
SCREW_VM_MODE_TORQUE_FROM_FORCE = "Da forza a coppia"
SCREW_VM_MODE_CHOICES = (
    SCREW_VM_MODE_FORCE_FROM_TORQUE,
    SCREW_VM_MODE_TORQUE_FROM_FORCE,
)
_SCREW_THREADS = tuple(SCREW_DB.list_threads())
SCREW_THREAD_CHOICES = tuple(t.name for t in _SCREW_THREADS) or ("-",)
SCREW_THREAD_FAMILY_CHOICES = tuple(dict.fromkeys(t.family for t in _SCREW_THREADS)) or ("-",)
SCREW_THREAD_CHOICES_BY_FAMILY = {
    family: tuple(t.name for t in _SCREW_THREADS if t.family == family) for family in SCREW_THREAD_FAMILY_CHOICES
}
SCREW_MATERIAL_CHOICES = tuple(SCREW_DB.list_material_names()) or ("-",)


def _spring_material(material_name: str) -> SpringMaterial:
    mat = SPRING_DB.get_by_name(material_name)
    if mat is None:
        raise ValueError(f"Materiale '{material_name}' non presente nel DB molle.")
    return mat


def _disc_spring_standard(spring_name: str) -> DiscSpringStandard:
    spring = SPRING_DB.get_disc_spring_by_name(spring_name)
    if spring is None:
        raise ValueError(f"Molla a tazza standard '{spring_name}' non presente nel DB.")
    return spring


def _spring_material_values(values: dict[str, CalcValue]) -> tuple[SpringMaterial, float, float, float, float]:
    materiale = str(values["materiale"])
    mat = _spring_material(materiale)
    E = float(values["mat_e"])
    G = float(values["mat_g"])
    sigma_amm = float(values["mat_sigma_amm"])
    tau_amm = float(values["mat_tau_amm"])
    _require_gt_zero("Materiale E", E)
    _require_gt_zero("Materiale G", G)
    _require_gt_zero("Materiale sigma amm", sigma_amm)
    _require_gt_zero("Materiale tau amm", tau_amm)
    return mat, E, G, sigma_amm, tau_amm


def _beam_material(material_name: str) -> BeamMaterial:
    mat = BEAM_DB.get_by_name(material_name)
    if mat is None:
        raise ValueError(f"Materiale trave '{material_name}' non presente nel DB.")
    return mat


def _beam_material_values(values: dict[str, CalcValue]) -> tuple[BeamMaterial, float, float, float, float]:
    materiale = str(values["materiale_trave"])
    mat = _beam_material(materiale)
    E = float(values["matb_e"])
    G = float(values["matb_g"])
    sigma_amm = float(values["matb_sigma_amm"])
    tau_amm = float(values["matb_tau_amm"])
    _require_gt_zero("Materiale trave E", E)
    _require_gt_zero("Materiale trave G", G)
    _require_gt_zero("Materiale trave sigma amm", sigma_amm)
    _require_gt_zero("Materiale trave tau amm", tau_amm)
    return mat, E, G, sigma_amm, tau_amm


def _beam_section_std(section_name: str) -> BeamSectionStandard:
    sec = BEAM_DB.get_section_by_name(section_name)
    if sec is None:
        raise ValueError(f"Sezione standard '{section_name}' non presente nel DB travi.")
    return sec


def _tol_material(material_name: str) -> ToleranceMaterial:
    mat = TOL_DB.get_material_by_name(material_name)
    if mat is None:
        raise ValueError(f"Materiale tolleranze '{material_name}' non presente nel DB.")
    return mat


def _tol_iso_zone(component: str, code: str, nominal_d_mm: float) -> IsoToleranceZone:
    zone = TOL_DB.get_iso_zone(component, code, nominal_d_mm)
    if zone is None:
        raise ValueError(
            f"Classe ISO '{code}' non disponibile per {component} al diametro nominale {_fmt_number(nominal_d_mm)} mm."
        )
    return zone


def _screw_thread_standard(thread_name: str) -> ScrewThreadStandard:
    thread = SCREW_DB.get_thread_by_name(thread_name)
    if thread is None:
        raise ValueError(f"Filettatura standard '{thread_name}' non presente nel DB.")
    return thread


def _screw_thread_names_by_family(family: str) -> tuple[str, ...]:
    family_key = (family or "").strip()
    options = SCREW_THREAD_CHOICES_BY_FAMILY.get(family_key)
    if options:
        return options
    return SCREW_THREAD_CHOICES


def _screw_nut_material(material_name: str) -> ScrewNutMaterial:
    mat = SCREW_DB.get_material_by_name(material_name)
    if mat is None:
        raise ValueError(f"Materiale '{material_name}' non presente nel DB vite-madrevite.")
    return mat


def _power_screw_profile_dims(d_mm: float, p_mm: float, thread: ScrewThreadStandard) -> tuple[float, float, float]:
    same_std = abs(d_mm - thread.d_mm) <= 1e-9 and abs(p_mm - thread.p_mm) <= 1e-9
    if same_std:
        return thread.d2_mm, thread.d3_mm, thread.d1_mm

    family = (thread.family or "").strip().upper()
    if "ISO M" in family:
        d2 = d_mm - (0.64952 * p_mm)
        d3 = d_mm - (1.22687 * p_mm)
        d1 = d_mm - (1.08253 * p_mm)
    elif "TRAPEZOIDALE" in family:
        d2 = d_mm - (0.5 * p_mm)
        d3 = d_mm - p_mm
        d1 = d_mm - (0.5 * p_mm)
    else:
        d2 = d_mm - (0.6 * p_mm)
        d3 = d_mm - (1.1 * p_mm)
        d1 = d_mm - (0.8 * p_mm)
    return d2, d3, d1


def _get_screw_material_category_from_name(name: str) -> str:
    """Estrae una categoria generica dal nome del materiale per vite/madrevite."""
    uname = (name or "").strip().upper()
    compact = "".join(ch for ch in uname if ch.isalnum())

    if "ACCIAIO INOX" in uname or "INOX" in uname or compact.startswith("AISI3"):
        return "ACCIAIO INOX"
    if "ACCIAIO" in uname or "C45" in compact or "42CRMO4" in compact:
        return "ACCIAIO"
    if "BRONZO" in uname or "CUSN" in compact:
        return "BRONZO"
    if "GHISA" in uname or "GJL" in compact:
        return "GHISA"
    return "SCONOSCIUTO"


def _get_suggested_mu(screw_mat_name: str, nut_mat_name: str) -> float | None:
    """
    Suggerisce un coefficiente di attrito basato sulla coppia di materiali.
    NOTA: Dati di esempio (attrito a secco), da sostituire con un DB dedicato.
    """
    screw_cat = _get_screw_material_category_from_name(screw_mat_name)
    nut_cat = _get_screw_material_category_from_name(nut_mat_name)
    if "SCONOSCIUTO" in (screw_cat, nut_cat):
        return None

    # Esempi di coppie (valori a secco). Le chiavi sono tuple ordinate per essere commutative.
    friction_pairs = {
        ("ACCIAIO", "ACCIAIO"): 0.15,
        ("ACCIAIO", "BRONZO"): 0.18,
        ("ACCIAIO INOX", "BRONZO"): 0.16,
        ("ACCIAIO", "GHISA"): 0.17,
    }

    key = tuple(sorted((screw_cat, nut_cat)))
    value = friction_pairs.get(key)
    if value is not None:
        return value

    # Fallback: se una coppia con ACCIAIO INOX non e' trovata, prova con ACCIAIO generico.
    c1, c2 = key
    has_inox = False
    if c1 == "ACCIAIO INOX":
        c1 = "ACCIAIO"
        has_inox = True
    if c2 == "ACCIAIO INOX":
        c2 = "ACCIAIO"
        has_inox = True

    if has_inox:
        fallback_key = tuple(sorted((c1, c2)))
        if fallback_key != key:
            return friction_pairs.get(fallback_key)

    return None


def _gear_correction_distribution(a_nom: float, module_ref: float, aw_raw: CalcValue, mode_raw: CalcValue) -> tuple[float, float, float, float]:
    _require_gt_zero("Modulo riferimento", module_ref)
    aw = a_nom if aw_raw is None else float(aw_raw)
    _require_gt_zero("Interasse target aw", aw)

    mode = str(mode_raw or GEAR_X_MODE_BOTH).strip()
    x_tot = (aw - a_nom) / module_ref
    if mode == GEAR_X_MODE_BOTH:
        x1 = 0.5 * x_tot
        x2 = 0.5 * x_tot
    elif mode == GEAR_X_MODE_PINION:
        x1 = x_tot
        x2 = 0.0
    elif mode == GEAR_X_MODE_WHEEL:
        x1 = 0.0
        x2 = x_tot
    else:
        raise ValueError("Ripartizione correzione x non valida.")
    return aw, x_tot, x1, x2


def _beam_section_properties(values: dict[str, CalcValue]) -> tuple[str, float, float, float, str]:
    sec_type = str(values["sezione_tipo"])
    if sec_type == BEAM_SECTION_ROUND:
        d = float(values["sec_d"])
        _require_gt_zero("Diametro tondo", d)
        area = math.pi * d**2 / 4.0
        inertia = math.pi * d**4 / 64.0
        w = inertia / (d / 2.0)
        return sec_type, area, inertia, w, f"d={_v(d, 'mm')}"

    if sec_type == BEAM_SECTION_TUBE:
        D = float(values["sec_D"])
        t = float(values["sec_t"])
        _require_gt_zero("Diametro esterno tubo", D)
        _require_gt_zero("Spessore tubo", t)
        di = D - (2.0 * t)
        if di <= 0:
            raise ValueError("Spessore tubo troppo grande (diametro interno <= 0).")
        area = math.pi * (D**2 - di**2) / 4.0
        inertia = math.pi * (D**4 - di**4) / 64.0
        w = inertia / (D / 2.0)
        return sec_type, area, inertia, w, f"D={_v(D, 'mm')}, t={_v(t, 'mm')}"

    if sec_type == BEAM_SECTION_RECT:
        b = float(values["sec_b"])
        h = float(values["sec_h"])
        _require_gt_zero("Base rettangolare b", b)
        _require_gt_zero("Altezza rettangolare h", h)
        area = b * h
        inertia = b * h**3 / 12.0
        w = inertia / (h / 2.0)
        return sec_type, area, inertia, w, f"b={_v(b, 'mm')}, h={_v(h, 'mm')}"

    if sec_type == BEAM_SECTION_RECT_TUBE:
        b = float(values["sec_b"])
        h = float(values["sec_h"])
        s = float(values["sec_s"])
        _require_gt_zero("Base tubolare b", b)
        _require_gt_zero("Altezza tubolare h", h)
        _require_gt_zero("Spessore tubolare s", s)
        bi = b - (2.0 * s)
        hi = h - (2.0 * s)
        if bi <= 0 or hi <= 0:
            raise ValueError("Spessore tubolare troppo grande (dimensioni interne <= 0).")
        area = (b * h) - (bi * hi)
        inertia = (b * h**3 - bi * hi**3) / 12.0
        w = inertia / (h / 2.0)
        return sec_type, area, inertia, w, f"b={_v(b, 'mm')}, h={_v(h, 'mm')}, s={_v(s, 'mm')}"

    if sec_type == BEAM_SECTION_STD:
        sec_name = str(values["sezione_std"])
        sec = _beam_section_std(sec_name)
        return (
            sec_type,
            sec.area_mm2,
            sec.ix_mm4,
            sec.wx_mm3,
            (
                f"{sec.name} ({sec.section_type}) "
                f"h={_v(sec.h_mm, 'mm')}, b={_v(sec.b_mm, 'mm')}, "
                f"tw={_v(sec.tw_mm, 'mm')}, tf={_v(sec.tf_mm, 'mm')}"
            ),
        )

    raise ValueError("Tipo sezione non valido.")


def _beam_torsion_section_properties(values: dict[str, CalcValue]) -> tuple[str, float, float, float, str]:
    sec_type = str(values["sezione_tipo"]).strip().upper()
    if sec_type not in BEAM_TORSION_SECTION_TYPES:
        raise ValueError("Per torsione sono ammesse solo: TONDO, TUBO, RETTANGOLARE, TUBOLARE.")

    if sec_type == BEAM_SECTION_ROUND:
        d = float(values["sec_d"])
        _require_gt_zero("Diametro tondo", d)
        area = math.pi * d**2 / 4.0
        j_t = math.pi * d**4 / 32.0
        r_max = d / 2.0
        return sec_type, area, j_t, r_max, f"d={_v(d, 'mm')}"

    if sec_type == BEAM_SECTION_TUBE:
        D = float(values["sec_D"])
        t = float(values["sec_t"])
        _require_gt_zero("Diametro esterno tubo", D)
        _require_gt_zero("Spessore tubo", t)
        di = D - (2.0 * t)
        if di <= 0:
            raise ValueError("Spessore tubo troppo grande (diametro interno <= 0).")
        area = math.pi * (D**2 - di**2) / 4.0
        j_t = math.pi * (D**4 - di**4) / 32.0
        r_max = D / 2.0
        return sec_type, area, j_t, r_max, f"D={_v(D, 'mm')}, t={_v(t, 'mm')}"

    if sec_type == BEAM_SECTION_RECT:
        b = float(values["sec_b"])
        h = float(values["sec_h"])
        _require_gt_zero("Base rettangolare b", b)
        _require_gt_zero("Altezza rettangolare h", h)
        a = max(b, h)
        c = min(b, h)
        beta = c / a if a > 0 else 0.0
        # Costante torsionale approssimata Saint-Venant per rettangolo pieno.
        j_t = (a * c**3) * (1.0 / 3.0 - 0.21 * beta * (1.0 - (beta**4 / 12.0)))
        area = b * h
        r_max = 0.5 * math.hypot(b, h)
        return sec_type, area, j_t, r_max, f"b={_v(b, 'mm')}, h={_v(h, 'mm')}"

    # BEAM_SECTION_RECT_TUBE
    b = float(values["sec_b"])
    h = float(values["sec_h"])
    s = float(values["sec_s"])
    _require_gt_zero("Base tubolare b", b)
    _require_gt_zero("Altezza tubolare h", h)
    _require_gt_zero("Spessore tubolare s", s)
    bi = b - (2.0 * s)
    hi = h - (2.0 * s)
    if bi <= 0 or hi <= 0:
        raise ValueError("Spessore tubolare troppo grande (dimensioni interne <= 0).")
    bm = b - s
    hm = h - s
    _require_gt_zero("Dimensione media tubolare bm", bm)
    _require_gt_zero("Dimensione media tubolare hm", hm)
    area = (b * h) - (bi * hi)
    am = bm * hm
    sum_l_over_t = 2.0 * ((bm / s) + (hm / s))
    # Approssimazione parete sottile chiusa per sezione rettangolare cava.
    j_t = 4.0 * (am**2) / sum_l_over_t
    r_max = 0.5 * math.hypot(b, h)
    return sec_type, area, j_t, r_max, f"b={_v(b, 'mm')}, h={_v(h, 'mm')}, s={_v(s, 'mm')}"


def _to_optional_float(value: CalcValue, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        return _as_float(txt, label)
    return float(value)


def _resolve_point(
    point_name: str,
    k: float,
    preload_force: float,
    freccia: float | None,
    forza: float | None,
) -> tuple[float, float, str | None]:
    if freccia is None and forza is None:
        raise ValueError(f"Compila almeno freccia o forza per il punto {point_name}.")
    if freccia is None and forza is not None:
        freccia = (forza - preload_force) / k
        return freccia, forza, None
    if forza is None and freccia is not None:
        forza = preload_force + (k * freccia)
        return freccia, forza, None

    assert freccia is not None and forza is not None
    forza_calc = preload_force + (k * freccia)
    delta = abs(forza_calc - forza)
    tol = max(0.5, 0.01 * max(abs(forza), abs(forza_calc)))
    note = None
    if delta > tol:
        note = (
            f"Punto {point_name}: dati non coerenti, "
            f"forza teorica={_fmt_number(forza_calc)} N, inserita={_fmt_number(forza)} N."
        )
    return freccia, forza, note


def _resolve_work_pairs(
    values: dict[str, CalcValue],
    k: float,
    preload_force: float = 0.0,
    deflection_label: str = "Freccia lavoro",
    deflection_unit: str = "mm",
) -> tuple[float, float, float, float, list[str]]:
    _require_gt_zero("Rigidezza k", k)
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    f1_in = _to_optional_float(values.get("f1"), f"{deflection_label} f1")
    f2_in = _to_optional_float(values.get("f2"), f"{deflection_label} f2")
    F1_in = _to_optional_float(values.get("F1"), "Forza lavoro F1")
    F2_in = _to_optional_float(values.get("F2"), "Forza lavoro F2")

    notes: list[str] = []

    if mode in (SPRING_CALC_MODE_FORCE_FROM_DEF, SPRING_CALC_MODE_FORCE_FROM_DEF_ANG):
        if f1_in is None or f2_in is None:
            raise ValueError(f"Con modo '{mode}' compila f1 e f2.")
        f1, f2 = f1_in, f2_in
        F1 = preload_force + (k * f1)
        F2 = preload_force + (k * f2)
        if F1_in is not None:
            delta1 = abs(F1_in - F1)
            if delta1 > max(0.5, 0.01 * max(abs(F1), abs(F1_in))):
                notes.append(
                    f"Punto 1: F1 inserita={_fmt_number(F1_in)} N, teorica={_fmt_number(F1)} N (usata teorica)."
                )
        if F2_in is not None:
            delta2 = abs(F2_in - F2)
            if delta2 > max(0.5, 0.01 * max(abs(F2), abs(F2_in))):
                notes.append(
                    f"Punto 2: F2 inserita={_fmt_number(F2_in)} N, teorica={_fmt_number(F2)} N (usata teorica)."
                )
    elif mode == SPRING_CALC_MODE_DEF_FROM_FORCE:
        if F1_in is None or F2_in is None:
            raise ValueError("Con modo 'F1/F2 N' compila F1 e F2.")
        F1, F2 = F1_in, F2_in
        f1 = (F1 - preload_force) / k
        f2 = (F2 - preload_force) / k
        if f1_in is not None:
            delta1 = abs(f1_in - f1)
            if delta1 > max(0.05, 0.01 * max(abs(f1), abs(f1_in))):
                notes.append(
                    f"Punto 1: f1 inserita={_fmt_number(f1_in)} {deflection_unit}, teorica={_fmt_number(f1)} {deflection_unit} (usata teorica)."
                )
        if f2_in is not None:
            delta2 = abs(f2_in - f2)
            if delta2 > max(0.05, 0.01 * max(abs(f2), abs(f2_in))):
                notes.append(
                    f"Punto 2: f2 inserita={_fmt_number(f2_in)} {deflection_unit}, teorica={_fmt_number(f2)} {deflection_unit} (usata teorica)."
                )
    else:
        raise ValueError("Modo calcolo non valido.")

    return f1, F1, f2, F2, notes


def _stress_check_rows(stress_label: str, stress_value: float, stress_limit: float) -> CalcRows:
    _require_gt_zero("Limite ammissibile materiale", stress_limit)
    if stress_value <= 0:
        return [
            ("Verifica stress", "Nessun carico significativo"),
            (f"{stress_label} amm.", _v(stress_limit, "MPa")),
        ]

    util = (stress_value / stress_limit) * 100.0
    safety = stress_limit / stress_value
    state = "OK" if stress_value <= stress_limit else "NON OK"
    return [
        (f"{stress_label} amm.", _v(stress_limit, "MPa")),
        ("Utilizzo materiale", _v(util, "%")),
        ("Fattore di sicurezza", _v(safety, digits=3)),
        ("Esito verifica", state),
    ]


def _section_row(title: str) -> tuple[str, str]:
    return (f"=== {title} ===", "")


def _work_points_rows(f1: float, F1: float, f2: float, F2: float, defl_unit: str = "mm") -> CalcRows:
    return [
        ("f1", _v(f1, defl_unit)),
        ("F1", _v(F1, "N")),
        ("f2", _v(f2, defl_unit)),
        ("F2", _v(F2, "N")),
        ("Delta f (f2-f1)", _v(f2 - f1, defl_unit)),
        ("Delta F (F2-F1)", _v(F2 - F1, "N")),
    ]


def _spring_material_field(material_choices: Sequence[str]) -> FieldSpec:
    if not material_choices:
        raise ValueError("DB materiali molle vuoto.")
    return FieldSpec(
        "materiale",
        "Materiale molla",
        material_choices[0],
        field_type="choice",
        choices=tuple(material_choices),
    )


def _spring_material_data_fields() -> tuple[FieldSpec, ...]:
    return (
        FieldSpec("mat_e", "Materiale E", "", "MPa"),
        FieldSpec("mat_g", "Materiale G", "", "MPa"),
        FieldSpec("mat_sigma_amm", "Materiale sigma amm", "", "MPa"),
        FieldSpec("mat_tau_amm", "Materiale tau amm", "", "MPa"),
    )


def _beam_material_field(material_choices: Sequence[str]) -> FieldSpec:
    if not material_choices:
        raise ValueError("DB materiali travi vuoto.")
    return FieldSpec(
        "materiale_trave",
        "Materiale trave",
        material_choices[0],
        field_type="choice",
        choices=tuple(material_choices),
    )


def _beam_material_data_fields() -> tuple[FieldSpec, ...]:
    return (
        FieldSpec("matb_e", "Materiale E", "", "MPa"),
        FieldSpec("matb_g", "Materiale G", "", "MPa"),
        FieldSpec("matb_sigma_amm", "Materiale sigma amm", "", "MPa"),
        FieldSpec("matb_tau_amm", "Materiale tau amm", "", "MPa"),
    )


def _spring_work_fields(
    deflection_mode_label: str = SPRING_CALC_MODE_FORCE_FROM_DEF,
    deflection_label: str = "Freccia lavoro",
    deflection_unit: str = "mm",
    f1_default: str = "5",
    f2_default: str = "10",
) -> tuple[FieldSpec, ...]:
    return (
        FieldSpec(
            "modo_calcolo",
            "Modo calcolo",
            deflection_mode_label,
            field_type="radio",
            choices=(deflection_mode_label, SPRING_CALC_MODE_DEF_FROM_FORCE),
        ),
        FieldSpec("f1", f"{deflection_label} f1", f1_default, deflection_unit, field_type="float_optional"),
        FieldSpec("F1", "Forza lavoro F1", "", "N", field_type="float_optional"),
        FieldSpec("f2", f"{deflection_label} f2", f2_default, deflection_unit, field_type="float_optional"),
        FieldSpec("F2", "Forza lavoro F2", "", "N", field_type="float_optional"),
    )


def _leaf_trapezoid_stiffness(
    E: float,
    n: int,
    t: float,
    L: float,
    b_fixed: float,
    b_free: float,
    steps: int = 400,
) -> float:
    _require_gt_zero("Numero lamine", float(n))
    _require_gt_zero("Spessore t", t)
    _require_gt_zero("Lunghezza L", L)
    _require_gt_zero("Larghezza lato fisso", b_fixed)
    _require_gt_zero("Larghezza lato libero", b_free)
    if steps < 2:
        steps = 2
    if steps % 2 != 0:
        steps += 1

    dx = L / steps
    integ = 0.0
    for i in range(steps + 1):
        x = i * dx
        b_x = b_fixed + ((b_free - b_fixed) * (x / L))
        term = ((L - x) ** 2) / b_x
        if i == 0 or i == steps:
            w = 1.0
        elif i % 2 == 1:
            w = 4.0
        else:
            w = 2.0
        integ += w * term
    integ *= dx / 3.0

    compliance = (12.0 * integ) / (E * n * t**3)
    if compliance <= 0:
        raise ValueError("Geometria lamina non valida.")
    return 1.0 / compliance


def calc_gear_spur(values: dict[str, float | int | str]) -> CalcRows:
    m = float(values["m"])
    z1 = int(values["z1"])
    z2 = int(values["z2"])
    alpha = float(values["alpha"])
    n1 = float(values["n1"])
    aw_raw = values.get("aw")
    x_mode = values.get("x_mode")

    _require_gt_zero("Modulo", m)
    _require_gt_zero("Denti pignone", z1)
    _require_gt_zero("Denti ruota", z2)
    _require_gt_zero("Angolo di pressione", alpha)
    _require_ge_zero("Velocita pignone", n1)

    i = z2 / z1
    d1 = m * z1
    d2 = m * z2
    a_nom = 0.5 * (d1 + d2)
    aw, x_tot, x1, x2 = _gear_correction_distribution(a_nom, m, aw_raw, x_mode)
    dw1 = (2.0 * aw * z1) / (z1 + z2)
    dw2 = (2.0 * aw * z2) / (z1 + z2)
    da1 = d1 + (2.0 * m * (1.0 + x1))
    da2 = d2 + (2.0 * m * (1.0 + x2))
    df1 = d1 - (2.0 * m * (1.25 - x1))
    df2 = d2 - (2.0 * m * (1.25 - x2))
    pb = math.pi * m * math.cos(math.radians(alpha))

    rows: CalcRows = [
        ("Rapporto di trasmissione i", _v(i, digits=6)),
        ("Diametro primitivo pignone d1", _v(d1, "mm")),
        ("Diametro primitivo ruota d2", _v(d2, "mm")),
        ("Interasse nominale a0", _v(a_nom, "mm")),
        ("Interasse di lavoro aw", _v(aw, "mm")),
        ("Correzione totale x_tot", _v(x_tot, digits=6)),
        ("Correzione pignone x1", _v(x1, digits=6)),
        ("Correzione ruota x2", _v(x2, digits=6)),
        ("Diametro primitivo lavoro pignone dw1", _v(dw1, "mm")),
        ("Diametro primitivo lavoro ruota dw2", _v(dw2, "mm")),
        ("Diametro esterno pignone da1", _v(da1, "mm")),
        ("Diametro esterno ruota da2", _v(da2, "mm")),
        ("Diametro di piede pignone df1", _v(df1, "mm")),
        ("Diametro di piede ruota df2", _v(df2, "mm")),
        ("Passo base pb", _v(pb, "mm")),
    ]
    if n1 > 0:
        rows.append(("Velocita ruota n2", _v(n1 / i, "rpm")))
    return rows


def calc_gear_helical(values: dict[str, float | int | str]) -> CalcRows:
    mn = float(values["mn"])
    beta = float(values["beta"])
    alpha = float(values.get("alpha", 20.0))
    z1 = int(values["z1"])
    z2 = int(values["z2"])
    n1 = float(values["n1"])
    aw_raw = values.get("aw")
    x_mode = values.get("x_mode")

    _require_gt_zero("Modulo normale", mn)
    _require_gt_zero("Angolo di pressione", alpha)
    _require_gt_zero("Denti pignone", z1)
    _require_gt_zero("Denti ruota", z2)
    _require_ge_zero("Velocita pignone", n1)
    if alpha >= 89.0:
        raise ValueError("Angolo di pressione troppo elevato.")
    if abs(beta) >= 89.0:
        raise ValueError("Angolo elica troppo elevato.")

    cos_b = math.cos(math.radians(beta))
    if abs(cos_b) < 1e-9:
        raise ValueError("Angolo elica non valido.")

    mt = mn / cos_b
    i = z2 / z1
    d1 = mt * z1
    d2 = mt * z2
    a_nom = 0.5 * (d1 + d2)
    aw, x_tot, x1, x2 = _gear_correction_distribution(a_nom, mt, aw_raw, x_mode)
    dw1 = (2.0 * aw * z1) / (z1 + z2)
    dw2 = (2.0 * aw * z2) / (z1 + z2)
    da1 = d1 + (2.0 * mt * (1.0 + x1))
    da2 = d2 + (2.0 * mt * (1.0 + x2))
    df1 = d1 - (2.0 * mt * (1.25 - x1))
    df2 = d2 - (2.0 * mt * (1.25 - x2))
    pn = math.pi * mn
    pbn = pn * math.cos(math.radians(alpha))
    tan_b = math.tan(math.radians(beta))
    px = float("inf") if abs(tan_b) < 1e-9 else pn / tan_b

    rows: CalcRows = [
        ("Rapporto di trasmissione i", _v(i, digits=6)),
        ("Modulo trasversale mt", _v(mt, "mm")),
        ("Angolo pressione alpha", _v(alpha, "gradi")),
        ("Diametro primitivo pignone d1", _v(d1, "mm")),
        ("Diametro primitivo ruota d2", _v(d2, "mm")),
        ("Interasse nominale a0", _v(a_nom, "mm")),
        ("Interasse di lavoro aw", _v(aw, "mm")),
        ("Correzione totale x_tot", _v(x_tot, digits=6)),
        ("Correzione pignone x1", _v(x1, digits=6)),
        ("Correzione ruota x2", _v(x2, digits=6)),
        ("Diametro primitivo lavoro pignone dw1", _v(dw1, "mm")),
        ("Diametro primitivo lavoro ruota dw2", _v(dw2, "mm")),
        ("Diametro esterno pignone da1", _v(da1, "mm")),
        ("Diametro esterno ruota da2", _v(da2, "mm")),
        ("Diametro di piede pignone df1", _v(df1, "mm")),
        ("Diametro di piede ruota df2", _v(df2, "mm")),
        ("Passo normale pn", _v(pn, "mm")),
        ("Passo base normale pbn", _v(pbn, "mm")),
        ("Passo assiale px", _v(px, "mm") if math.isfinite(px) else "infinito (beta=0)"),
    ]
    if n1 > 0:
        rows.append(("Velocita ruota n2", _v(n1 / i, "rpm")))
    return rows


def _bevel_angles(z1: int, z2: int, sigma_deg: float) -> tuple[float, float]:
    sigma = math.radians(sigma_deg)
    i = z2 / z1
    den1 = i + math.cos(sigma)
    den2 = (1.0 / i) + math.cos(sigma)
    if abs(den1) < 1e-10 or abs(den2) < 1e-10:
        raise ValueError("Combinazione z/sigma non valida.")
    delta1 = math.degrees(math.atan(math.sin(sigma) / den1))
    delta2 = math.degrees(math.atan(math.sin(sigma) / den2))
    return delta1, delta2


def calc_gear_bevel_spur(values: dict[str, float | int | str]) -> CalcRows:
    m = float(values["m"])
    z1 = int(values["z1"])
    z2 = int(values["z2"])
    sigma = float(values["sigma"])

    _require_gt_zero("Modulo", m)
    _require_gt_zero("Denti pignone", z1)
    _require_gt_zero("Denti ruota", z2)
    if sigma <= 0 or sigma >= 180:
        raise ValueError("Angolo assi sigma deve essere compreso tra 0 e 180 gradi.")

    i = z2 / z1
    delta1, delta2 = _bevel_angles(z1, z2, sigma)
    d1 = m * z1
    d2 = m * z2
    sin_d1 = math.sin(math.radians(delta1))
    if abs(sin_d1) < 1e-9:
        raise ValueError("Geometria conica non valida.")
    R = d1 / (2.0 * sin_d1)

    return [
        ("Rapporto di trasmissione i", _v(i, digits=6)),
        ("Diametro primitivo pignone d1", _v(d1, "mm")),
        ("Diametro primitivo ruota d2", _v(d2, "mm")),
        ("Angolo cono pignone delta1", _v(delta1, "gradi")),
        ("Angolo cono ruota delta2", _v(delta2, "gradi")),
        ("Distanza cono R", _v(R, "mm")),
    ]


def calc_gear_bevel_helical(values: dict[str, float | int | str]) -> CalcRows:
    mn = float(values["mn"])
    beta = float(values["beta"])
    alpha = float(values.get("alpha", 20.0))
    z1 = int(values["z1"])
    z2 = int(values["z2"])
    sigma = float(values["sigma"])

    _require_gt_zero("Modulo normale", mn)
    _require_gt_zero("Angolo di pressione", alpha)
    _require_gt_zero("Denti pignone", z1)
    _require_gt_zero("Denti ruota", z2)
    if sigma <= 0 or sigma >= 180:
        raise ValueError("Angolo assi sigma deve essere compreso tra 0 e 180 gradi.")
    if alpha >= 89.0:
        raise ValueError("Angolo di pressione troppo elevato.")
    if abs(beta) >= 89.0:
        raise ValueError("Angolo elica troppo elevato.")

    cos_b = math.cos(math.radians(beta))
    if abs(cos_b) < 1e-9:
        raise ValueError("Angolo elica non valido.")

    mt = mn / cos_b
    i = z2 / z1
    d1 = mt * z1
    d2 = mt * z2
    delta1, delta2 = _bevel_angles(z1, z2, sigma)
    zv1 = z1 / (cos_b**3)
    zv2 = z2 / (cos_b**3)

    sin_d1 = math.sin(math.radians(delta1))
    if abs(sin_d1) < 1e-9:
        raise ValueError("Geometria conica non valida.")
    R = d1 / (2.0 * sin_d1)

    return [
        ("Rapporto di trasmissione i", _v(i, digits=6)),
        ("Modulo trasversale mt", _v(mt, "mm")),
        ("Angolo pressione alpha", _v(alpha, "gradi")),
        ("Diametro primitivo pignone d1", _v(d1, "mm")),
        ("Diametro primitivo ruota d2", _v(d2, "mm")),
        ("Angolo cono pignone delta1", _v(delta1, "gradi")),
        ("Angolo cono ruota delta2", _v(delta2, "gradi")),
        ("Numero denti virtuali pignone zv1", _v(zv1)),
        ("Numero denti virtuali ruota zv2", _v(zv2)),
        ("Distanza cono R", _v(R, "mm")),
    ]


def calc_gear_worm(values: dict[str, float | int | str]) -> CalcRows:
    m = float(values["m"])
    z1 = int(values["z1"])
    z2 = int(values["z2"])
    q = float(values["q"])
    n1 = float(values["n1"])

    _require_gt_zero("Modulo", m)
    _require_gt_zero("Principi vite", z1)
    _require_gt_zero("Denti ruota", z2)
    _require_gt_zero("Fattore diametrale q", q)
    _require_ge_zero("Velocita vite", n1)

    i = z2 / z1
    d1 = q * m
    d2 = z2 * m
    a = 0.5 * (d1 + d2)
    gamma = math.degrees(math.atan(z1 / q))
    lead = math.pi * m * z1

    rows: CalcRows = [
        ("Rapporto di trasmissione i", _v(i, digits=6)),
        ("Diametro primitivo vite d1", _v(d1, "mm")),
        ("Diametro primitivo ruota d2", _v(d2, "mm")),
        ("Interasse a", _v(a, "mm")),
        ("Angolo di avanzamento gamma", _v(gamma, "gradi")),
        ("Passo elica (lead) pz", _v(lead, "mm/giro")),
    ]
    if n1 > 0:
        rows.append(("Velocita ruota n2", _v(n1 / i, "rpm")))
    return rows


def calc_power_screw(values: dict[str, CalcValue]) -> CalcRows:
    thread_name = str(values["vm_thread_std"]).strip()
    if not thread_name or thread_name == "-":
        raise ValueError("Seleziona una filettatura standard da DB.")
    thread = _screw_thread_standard(thread_name)

    d = float(values["vm_d"])
    p = float(values["vm_p"])
    mu = float(values["vm_mu"])
    Le = float(values["vm_Le"])
    mode = str(values["vm_mode"]).strip()
    T_in = values.get("vm_T")
    F_in = values.get("vm_F")

    _require_gt_zero("Diametro vite d", d)
    _require_gt_zero("Passo p", p)
    _require_gt_zero("Lunghezza madrevite Le", Le)
    _require_ge_zero("Attrito mu", mu)

    mat_screw_name = str(values["vm_mat_screw"]).strip()
    mat_nut_name = str(values["vm_mat_nut"]).strip()
    if not mat_screw_name or mat_screw_name == "-":
        raise ValueError("Seleziona il materiale vite da DB.")
    if not mat_nut_name or mat_nut_name == "-":
        raise ValueError("Seleziona il materiale madrevite da DB.")

    mat_screw = _screw_nut_material(mat_screw_name)
    mat_nut = _screw_nut_material(mat_nut_name)

    suggested_mu = _get_suggested_mu(mat_screw.name, mat_nut.name)

    d2, d3, d1 = _power_screw_profile_dims(d, p, thread)
    if d2 <= 0 or d3 <= 0 or d1 <= 0:
        raise ValueError("Geometria filettatura non valida (diametri interni <= 0).")

    lambda_rad = math.atan(p / (math.pi * d2))
    half_flank_rad = math.radians(thread.flank_angle_deg * 0.5)
    cos_half = math.cos(half_flank_rad)
    if abs(cos_half) < 1e-9:
        raise ValueError("Angolo filettatura non valido.")
    rho_rad = math.atan(mu / cos_half)
    den = math.tan(lambda_rad + rho_rad)
    if den <= 0:
        raise ValueError("Configurazione attrito/elica non valida.")

    if mode == SCREW_VM_MODE_FORCE_FROM_TORQUE:
        if T_in is None:
            raise ValueError("Compila la coppia T per il modo 'Da coppia a forza'.")
        T_nm = float(T_in)
        _require_gt_zero("Coppia T", T_nm)
        T_nmm = T_nm * 1000.0
        F = (2.0 * T_nmm) / (d2 * den)
    elif mode == SCREW_VM_MODE_TORQUE_FROM_FORCE:
        if F_in is None:
            raise ValueError("Compila la forza F per il modo 'Da forza a coppia'.")
        F = float(F_in)
        _require_gt_zero("Forza assiale F", F)
        T_nmm = F * (d2 * 0.5) * den
        T_nm = T_nmm / 1000.0
    else:
        raise ValueError("Modo calcolo vite-madrevite non valido.")

    eta_den = math.tan(lambda_rad + rho_rad)
    eta = math.tan(lambda_rad) / eta_den if abs(eta_den) > 1e-12 else 0.0
    is_self_locking = lambda_rad <= rho_rad

    area_core = math.pi * d3**2 / 4.0
    sigma_ax = F / area_core
    tau_tor = (16.0 * T_nmm) / (math.pi * d3**3)
    sigma_vm = math.sqrt(sigma_ax**2 + (3.0 * tau_tor**2))

    area_press = 0.5 * math.pi * d2 * Le
    p_bearing = F / area_press

    area_shear_screw = 0.5 * math.pi * d3 * Le
    area_shear_nut = 0.5 * math.pi * d1 * Le
    tau_thread_screw = F / area_shear_screw
    tau_thread_nut = F / area_shear_nut

    def _sf(limit_value: float, stress_value: float) -> float:
        if stress_value <= 1e-12:
            return float("inf")
        return limit_value / stress_value

    sf_vm_screw = _sf(mat_screw.sigma_amm_mpa, sigma_vm)
    sf_tau_screw = _sf(mat_screw.tau_amm_mpa, tau_thread_screw)
    sf_press_nut = _sf(mat_nut.sigma_amm_mpa, p_bearing)
    sf_tau_nut = _sf(mat_nut.tau_amm_mpa, tau_thread_nut)
    sf_min_global = min(sf_vm_screw, sf_tau_screw, sf_press_nut, sf_tau_nut)

    screw_ok = sigma_vm <= mat_screw.sigma_amm_mpa and tau_thread_screw <= mat_screw.tau_amm_mpa
    nut_ok = p_bearing <= mat_nut.sigma_amm_mpa and tau_thread_nut <= mat_nut.tau_amm_mpa
    overall_ok = screw_ok and nut_ok
    rows: CalcRows = [
        ("Geometria filettatura", ""),
        ("Standard selezionato", thread.name),
        ("Famiglia", thread.family),
        ("Diametro nominale d", _v(d, "mm")),
        ("Passo p", _v(p, "mm")),
        ("Diametro medio d2", _v(d2, "mm")),
        ("Diametro nocciolo vite d3", _v(d3, "mm")),
        ("Diametro interno madrevite d1", _v(d1, "mm")),
        ("Angolo elica lambda", _v(math.degrees(lambda_rad), "gradi")),
        ("Angolo attrito ridotto rho", _v(math.degrees(rho_rad), "gradi")),
        ("Rendimento eta", _v(eta * 100.0, "%")),
        ("Autobloccaggio", "SI" if is_self_locking else "NO"),
        ("", ""),
        ("Funzionamento", ""),
        ("Modo calcolo", mode),
        ("Coppia T", _v(T_nm, "Nm")),
        ("Forza assiale F", _v(F, "N")),
        ("Lunghezza madrevite Le", _v(Le, "mm")),
        ("Attrito mu", _v(mu, digits=4)),
        ("", ""),
        ("Verifica vite", ""),
        ("Materiale vite", mat_screw.name),
        ("Sigma assiale vite", _v(sigma_ax, "MPa")),
        ("Tau torsionale vite", _v(tau_tor, "MPa")),
        ("Sigma equivalente von Mises", _v(sigma_vm, "MPa")),
        ("Sigma amm vite", _v(mat_screw.sigma_amm_mpa, "MPa")),
        ("Tau amm vite", _v(mat_screw.tau_amm_mpa, "MPa")),
        ("SF sigma_vM vite", _v(sf_vm_screw, digits=4)),
        ("SF tau filetto vite", _v(sf_tau_screw, digits=4)),
        ("Esito vite", "OK" if screw_ok else "NON OK"),
        ("", ""),
        ("Verifica madrevite", ""),
        ("Materiale madrevite", mat_nut.name),
        ("Pressione media filetto", _v(p_bearing, "MPa")),
        ("Tau filetto madrevite", _v(tau_thread_nut, "MPa")),
        ("Pressione amm madrevite", _v(mat_nut.sigma_amm_mpa, "MPa")),
        ("Tau amm madrevite", _v(mat_nut.tau_amm_mpa, "MPa")),
        ("SF pressione madrevite", _v(sf_press_nut, digits=4)),
        ("SF tau filetto madrevite", _v(sf_tau_nut, digits=4)),
        ("Esito madrevite", "OK" if nut_ok else "NON OK"),
        ("", ""),
        ("Riepilogo", ""),
        ("SF minimo globale", _v(sf_min_global, digits=4)),
        ("Esito globale", "OK" if overall_ok else "NON OK"),
    ]

    if suggested_mu is not None:
        rows.insert(19, ("Attrito suggerito (a secco)", _v(suggested_mu, digits=3)))

    return rows


def calc_spring_comp_round(values: dict[str, CalcValue]) -> CalcRows:
    terminale = str(values["terminale"])
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    d = float(values["d"])
    Dm = float(values["Dm"])
    Na = float(values["Na"])
    L0 = float(values["L0"])
    mat, _E, G, _sigma_amm, tau_amm = _spring_material_values(values)

    _require_gt_zero("Diametro filo", d)
    _require_gt_zero("Diametro medio", Dm)
    _require_gt_zero("Spire attive", Na)
    _require_gt_zero("Lunghezza libera L0", L0)
    if Dm <= d:
        raise ValueError("Diametro medio deve essere maggiore del diametro filo.")

    n_inactive = 0 if terminale == "APERTE" else 2
    Nt = Na + n_inactive
    De = Dm + d
    Di = Dm - d
    C = Dm / d
    if C <= 1.1:
        raise ValueError("Indice molla C troppo basso.")

    k = (G * d**4) / (8.0 * Dm**3 * Na)
    f1, F1, f2, F2, notes = _resolve_work_pairs(values, k, preload_force=0.0)
    Fmax = max(abs(F1), abs(F2))
    fmax = max(abs(f1), abs(f2))

    Kw = ((4.0 * C - 1.0) / (4.0 * C - 4.0)) + (0.615 / C)
    tau = 0.0 if Fmax == 0 else Kw * ((8.0 * Fmax * Dm) / (math.pi * d**3))
    tau1 = 0.0 if F1 == 0 else Kw * ((8.0 * abs(F1) * Dm) / (math.pi * d**3))
    tau2 = 0.0 if F2 == 0 else Kw * ((8.0 * abs(F2) * Dm) / (math.pi * d**3))
    Ls = Nt * d
    Lmin = L0 - fmax
    margine_blocco = Lmin - Ls
    esito_blocco = "OK" if margine_blocco > 0 else "NON OK"

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale", mat.name),
        ("Terminali", terminale),
        ("Modo calcolo", mode),
        ("Diametro filo d", _v(d, "mm")),
        ("Diametro medio Dm", _v(Dm, "mm")),
        ("Spire attive Na", _v(Na)),
        ("Spire totali Nt", _v(Nt)),
        ("Diametro esterno De", _v(De, "mm")),
        ("Diametro interno Di", _v(Di, "mm")),
        ("Indice molla C", _v(C, digits=6)),
        _section_row("CONDIZIONI DI LAVORO"),
        ("Modulo taglio G", _v(G, "MPa")),
        ("Rigidezza k", _v(k, "N/mm")),
        ("Fattore Wahl Kw", _v(Kw, digits=6)),
        ("Forza massima lavoro Fmax", _v(Fmax, "N")),
        ("Lunghezza a blocco Ls", _v(Ls, "mm")),
        ("Lunghezza libera progetto L0", _v(L0, "mm")),
        ("Lunghezza minima lavoro Lmin", _v(Lmin, "mm")),
        ("Margine a blocco (Lmin-Ls)", _v(margine_blocco, "mm")),
        ("Esito blocco", esito_blocco),
        _section_row("DATI PUNTI DI LAVORO"),
        *_work_points_rows(f1, F1, f2, F2, "mm"),
        ("Tau punto 1", _v(tau1, "MPa")),
        ("Tau punto 2", _v(tau2, "MPa")),
        _section_row("VERIFICA MATERIALE"),
        ("Tensione max tau", _v(tau, "MPa")),
    ]
    rows.extend(_stress_check_rows("Tau", tau, tau_amm))
    if notes:
        rows.append(("Note punti lavoro", " | ".join(notes)))
    return rows


def calc_spring_comp_rect(values: dict[str, CalcValue]) -> CalcRows:
    terminale = str(values["terminale"])
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    b = float(values["b"])
    h = float(values["h"])
    Dm = float(values["Dm"])
    Na = float(values["Na"])
    L0 = float(values["L0"])
    mat, _E, G, _sigma_amm, tau_amm = _spring_material_values(values)

    _require_gt_zero("Larghezza sezione b", b)
    _require_gt_zero("Altezza sezione h", h)
    _require_gt_zero("Diametro medio", Dm)
    _require_gt_zero("Spire attive", Na)
    _require_gt_zero("Lunghezza libera L0", L0)

    area = b * h
    deq = math.sqrt((4.0 * area) / math.pi)
    if Dm <= deq:
        raise ValueError("Diametro medio troppo piccolo rispetto alla sezione.")

    n_inactive = 0 if terminale == "APERTE" else 2
    Nt = Na + n_inactive
    De = Dm + deq
    Di = Dm - deq
    C = Dm / deq
    if C <= 1.1:
        raise ValueError("Indice molla equivalente C troppo basso.")

    k = (G * deq**4) / (8.0 * Dm**3 * Na)
    f1, F1, f2, F2, notes = _resolve_work_pairs(values, k, preload_force=0.0)
    Fmax = max(abs(F1), abs(F2))
    fmax = max(abs(f1), abs(f2))
    tau_eq = 0.0 if Fmax == 0 else (8.0 * Fmax * Dm) / (math.pi * deq**3)
    tau1 = 0.0 if F1 == 0 else (8.0 * abs(F1) * Dm) / (math.pi * deq**3)
    tau2 = 0.0 if F2 == 0 else (8.0 * abs(F2) * Dm) / (math.pi * deq**3)
    Ls = Nt * deq
    Lmin = L0 - fmax
    margine_blocco = Lmin - Ls
    esito_blocco = "OK" if margine_blocco > 0 else "NON OK"

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale", mat.name),
        ("Terminali", terminale),
        ("Modo calcolo", mode),
        ("Larghezza b", _v(b, "mm")),
        ("Altezza h", _v(h, "mm")),
        ("Diametro medio Dm", _v(Dm, "mm")),
        ("Spire attive Na", _v(Na)),
        ("Spire totali Nt", _v(Nt)),
        ("Diametro esterno De", _v(De, "mm")),
        ("Diametro interno Di", _v(Di, "mm")),
        ("Diametro equivalente deq", _v(deq, "mm")),
        ("Indice equivalente C", _v(C, digits=6)),
        _section_row("CONDIZIONI DI LAVORO"),
        ("Modulo taglio G", _v(G, "MPa")),
        ("Rigidezza k", _v(k, "N/mm")),
        ("Forza massima lavoro Fmax", _v(Fmax, "N")),
        ("Lunghezza a blocco Ls", _v(Ls, "mm")),
        ("Lunghezza libera progetto L0", _v(L0, "mm")),
        ("Lunghezza minima lavoro Lmin", _v(Lmin, "mm")),
        ("Margine a blocco (Lmin-Ls)", _v(margine_blocco, "mm")),
        ("Esito blocco", esito_blocco),
        ("Nota modello", "Equivalenza sezione rettangolare -> tonda"),
        _section_row("DATI PUNTI DI LAVORO"),
        *_work_points_rows(f1, F1, f2, F2, "mm"),
        ("Tau punto 1", _v(tau1, "MPa")),
        ("Tau punto 2", _v(tau2, "MPa")),
        _section_row("VERIFICA MATERIALE"),
        ("Tensione equivalente tau", _v(tau_eq, "MPa")),
    ]
    rows.extend(_stress_check_rows("Tau", tau_eq, tau_amm))
    if notes:
        rows.append(("Note punti lavoro", " | ".join(notes)))
    return rows


def calc_spring_extension_round(values: dict[str, CalcValue]) -> CalcRows:
    terminale = str(values["terminale"])
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    d = float(values["d"])
    Dm = float(values["Dm"])
    Na = float(values["Na"])
    F0 = float(values["F0"])
    mat, _E, G, _sigma_amm, tau_amm = _spring_material_values(values)

    _require_gt_zero("Diametro filo", d)
    _require_gt_zero("Diametro medio", Dm)
    _require_gt_zero("Spire attive", Na)
    _require_ge_zero("Trazione iniziale F0", F0)
    if Dm <= d:
        raise ValueError("Diametro medio deve essere maggiore del diametro filo.")

    C = Dm / d
    if C <= 1.1:
        raise ValueError("Indice molla C troppo basso.")

    k = (G * d**4) / (8.0 * Dm**3 * Na)
    f1, F1, f2, F2, notes = _resolve_work_pairs(values, k, preload_force=F0)
    Fmax = max(abs(F1), abs(F2))
    x_max = max(max(F1 - F0, 0.0), max(F2 - F0, 0.0)) / k if k > 0 else 0.0
    Kw = ((4.0 * C - 1.0) / (4.0 * C - 4.0)) + (0.615 / C)
    tau = 0.0 if Fmax == 0 else Kw * ((8.0 * Fmax * Dm) / (math.pi * d**3))
    tau1 = 0.0 if F1 == 0 else Kw * ((8.0 * abs(F1) * Dm) / (math.pi * d**3))
    tau2 = 0.0 if F2 == 0 else Kw * ((8.0 * abs(F2) * Dm) / (math.pi * d**3))
    Ls = (Na + 2.0) * d

    extra_notes: list[str] = []
    if F1 < F0:
        extra_notes.append("Punto 1: F1 < F0, molla non in allungamento utile.")
    if F2 < F0:
        extra_notes.append("Punto 2: F2 < F0, molla non in allungamento utile.")

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale", mat.name),
        ("Terminali", terminale),
        ("Modo calcolo", mode),
        ("Diametro filo d", _v(d, "mm")),
        ("Diametro medio Dm", _v(Dm, "mm")),
        ("Spire attive Na", _v(Na)),
        ("Indice molla C", _v(C, digits=6)),
        _section_row("CONDIZIONI DI LAVORO"),
        ("Modulo taglio G", _v(G, "MPa")),
        ("Rigidezza k", _v(k, "N/mm")),
        ("Precarico iniziale F0", _v(F0, "N")),
        ("Allungamento attivo max x_max", _v(x_max, "mm")),
        ("Lunghezza corpo molla a blocco Ls", _v(Ls, "mm")),
        ("Fattore Wahl Kw", _v(Kw, digits=6)),
        _section_row("DATI PUNTI DI LAVORO"),
        *_work_points_rows(f1, F1, f2, F2, "mm"),
        ("Tau punto 1", _v(tau1, "MPa")),
        ("Tau punto 2", _v(tau2, "MPa")),
        _section_row("VERIFICA MATERIALE"),
        ("Tensione max tau", _v(tau, "MPa")),
    ]
    rows.extend(_stress_check_rows("Tau", tau, tau_amm))
    all_notes = notes + extra_notes
    if all_notes:
        rows.append(("Note punti lavoro", " | ".join(all_notes)))
    return rows


def calc_spring_torsion_round(values: dict[str, CalcValue]) -> CalcRows:
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    d = float(values["d"])
    Dm = float(values["Dm"])
    Nb = float(values["Nb"])
    leva = float(values["leva"])
    mat, E, _G, sigma_amm, _tau_amm = _spring_material_values(values)

    _require_gt_zero("Diametro filo", d)
    _require_gt_zero("Diametro medio", Dm)
    _require_gt_zero("Spire attive", Nb)
    _require_gt_zero("Leva efficace", leva)
    if Dm <= d:
        raise ValueError("Diametro medio deve essere maggiore del diametro filo.")

    C = Dm / d
    if C <= 1.1:
        raise ValueError("Indice molla C troppo basso.")

    k_deg = (E * d**4) / (10.8 * Dm * Nb)
    k_force_deg = k_deg / leva
    k_rad = k_deg * (180.0 / math.pi)
    k_lin = k_rad / (leva**2)
    f1, F1, f2, F2, notes = _resolve_work_pairs(
        values,
        k_force_deg,
        preload_force=0.0,
        deflection_label="Angolo lavoro",
        deflection_unit="°",
    )

    M1 = F1 * leva
    M2 = F2 * leva
    Mmax = max(abs(M1), abs(M2))
    fmax = max(abs(f1), abs(f2))
    theta1_deg = f1
    theta2_deg = f2
    theta1_rad = math.radians(theta1_deg)
    theta2_rad = math.radians(theta2_deg)
    theta_max_deg = fmax
    Ki = ((4.0 * C * C) - C - 1.0) / (4.0 * C * (C - 1.0))
    sigma = 0.0 if Mmax == 0 else (32.0 * Ki * Mmax) / (math.pi * d**3)
    sigma1 = 0.0 if M1 == 0 else (32.0 * Ki * abs(M1)) / (math.pi * d**3)
    sigma2 = 0.0 if M2 == 0 else (32.0 * Ki * abs(M2)) / (math.pi * d**3)

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale", mat.name),
        ("Modo calcolo", mode),
        ("Diametro filo d", _v(d, "mm")),
        ("Diametro medio Dm", _v(Dm, "mm")),
        ("Spire attive Nb", _v(Nb)),
        ("Leva efficace", _v(leva, "mm")),
        ("Indice molla C", _v(C, digits=6)),
        _section_row("CONDIZIONI DI LAVORO"),
        ("Modulo elastico E", _v(E, "MPa")),
        ("Rigidezza angolare k", _v(k_deg, "Nmm/grado")),
        ("Rigidezza forza/angolo kF", _v(k_force_deg, "N/grado")),
        ("Rigidezza lineare k", _v(k_lin, "N/mm")),
        ("Momento massimo Mmax", _v(Mmax, "Nmm")),
        ("Angolo massimo theta max", _v(theta_max_deg, "gradi")),
        _section_row("DATI PUNTI DI LAVORO"),
        ("f1", _v(f1, "gradi")),
        ("F1", _v(F1, "N")),
        ("M1", _v(M1, "Nmm")),
        ("theta1", _v(theta1_deg, "gradi")),
        ("f2", _v(f2, "gradi")),
        ("F2", _v(F2, "N")),
        ("M2", _v(M2, "Nmm")),
        ("theta2", _v(theta2_deg, "gradi")),
        ("Sigma punto 1", _v(sigma1, "MPa")),
        ("Sigma punto 2", _v(sigma2, "MPa")),
        ("Delta f (f2-f1)", _v(f2 - f1, "gradi")),
        ("Delta F (F2-F1)", _v(F2 - F1, "N")),
        _section_row("VERIFICA MATERIALE"),
        ("Fattore correzione Ki", _v(Ki, digits=6)),
        ("Tensione max sigma", _v(sigma, "MPa")),
    ]
    rows.extend(_stress_check_rows("Sigma", sigma, sigma_amm))
    if notes:
        rows.append(("Note punti lavoro", " | ".join(notes)))
    return rows


def calc_spring_leaf(values: dict[str, CalcValue]) -> CalcRows:
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    n = int(values["n"])
    b_fixed = float(values["b_fixed"])
    b_free = float(values["b_free"])
    t = float(values["t"])
    L = float(values["L"])
    mat, E, _G, sigma_amm, _tau_amm = _spring_material_values(values)

    _require_gt_zero("Numero lamine", n)
    _require_gt_zero("Larghezza lato fisso", b_fixed)
    _require_gt_zero("Larghezza lato libero", b_free)
    _require_gt_zero("Spessore lamina t", t)
    _require_gt_zero("Lunghezza libera L", L)

    k = _leaf_trapezoid_stiffness(E, n, t, L, b_fixed, b_free)
    f1, F1, f2, F2, notes = _resolve_work_pairs(values, k, preload_force=0.0)
    Fmax = max(abs(F1), abs(F2))
    fmax = max(abs(f1), abs(f2))
    sigma = 0.0 if Fmax == 0 else (6.0 * Fmax * L) / (n * b_fixed * t**2)
    sigma1 = 0.0 if F1 == 0 else (6.0 * abs(F1) * L) / (n * b_fixed * t**2)
    sigma2 = 0.0 if F2 == 0 else (6.0 * abs(F2) * L) / (n * b_fixed * t**2)
    b_mean = 0.5 * (b_fixed + b_free)
    taper_ratio = b_free / b_fixed

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale", mat.name),
        ("Modo calcolo", mode),
        ("Numero lamine n", _v(n)),
        ("Larghezza lato fisso", _v(b_fixed, "mm")),
        ("Larghezza lato libero", _v(b_free, "mm")),
        ("Larghezza media", _v(b_mean, "mm")),
        ("Rapporto trapezio (bl/bf)", _v(taper_ratio, digits=6)),
        ("Spessore t", _v(t, "mm")),
        ("Lunghezza libera L", _v(L, "mm")),
        _section_row("CONDIZIONI DI LAVORO"),
        ("Modulo elastico E", _v(E, "MPa")),
        ("Rigidezza k", _v(k, "N/mm")),
        ("Freccia massima lavoro fmax", _v(fmax, "mm")),
        ("Forza massima lavoro Fmax", _v(Fmax, "N")),
        _section_row("DATI PUNTI DI LAVORO"),
        *_work_points_rows(f1, F1, f2, F2, "mm"),
        ("Sigma punto 1", _v(sigma1, "MPa")),
        ("Sigma punto 2", _v(sigma2, "MPa")),
        _section_row("VERIFICA MATERIALE"),
        ("Tensione max sigma", _v(sigma, "MPa")),
        ("Schema", "Lamina a sbalzo trapezoidale con carico in punta"),
    ]
    rows.extend(_stress_check_rows("Sigma", sigma, sigma_amm))
    if notes:
        rows.append(("Note punti lavoro", " | ".join(notes)))
    return rows


def calc_spring_disc(values: dict[str, CalcValue]) -> CalcRows:
    mode = str(values.get("modo_calcolo") or SPRING_CALC_MODE_FORCE_FROM_DEF)
    source = str(values.get("tazza_source") or DISC_SPRING_SOURCE_CUSTOM)
    std_name = str(values.get("tazza_std") or "").strip()
    n_series = int(values["n_series"])
    n_parallel = int(values["n_parallel"])
    std: DiscSpringStandard | None = None

    if source == DISC_SPRING_SOURCE_DB:
        if not std_name:
            raise ValueError("Seleziona la molla a tazza standard.")
        std = _disc_spring_standard(std_name)
        Do = std.do_mm
        Di = std.di_mm
        t = std.t_mm
        h0 = std.h0_mm
    else:
        Do = float(values["Do"])
        Di = float(values["Di"])
        t = float(values["t"])
        h0 = float(values["h0"])

    nu = float(values["nu"])
    mat, E, _G, sigma_amm, _tau_amm = _spring_material_values(values)

    _require_gt_zero("Diametro esterno Do", Do)
    _require_gt_zero("Diametro interno Di", Di)
    _require_gt_zero("Spessore t", t)
    _require_gt_zero("Altezza conica h0", h0)
    _require_gt_zero("Numero molle in serie", float(n_series))
    _require_gt_zero("Numero molle in parallelo", float(n_parallel))
    if Do <= Di:
        raise ValueError("Do deve essere maggiore di Di.")
    if nu <= 0 or nu >= 0.5:
        raise ValueError("Poisson nu deve essere compreso tra 0 e 0.5.")

    Dm = 0.5 * (Do + Di)
    k_single = (4.0 * E * t**3) / (3.0 * (1.0 - nu**2) * Dm**2)
    k_eq = k_single * (n_parallel / n_series)

    f1, F1, f2, F2, notes = _resolve_work_pairs(values, k_eq, preload_force=0.0)
    Fmax = max(abs(F1), abs(F2))
    smax = max(abs(f1), abs(f2))
    F1_single = F1 / n_parallel
    F2_single = F2 / n_parallel
    Fmax_single = Fmax / n_parallel
    s1_single = f1 / n_series
    s2_single = f2 / n_series
    smax_single = smax / n_series

    sigma = 0.0 if Fmax_single == 0 else (4.0 * Fmax_single * Dm) / (math.pi * (Do - Di) * t**2)
    sigma1 = 0.0 if F1_single == 0 else (4.0 * abs(F1_single) * Dm) / (math.pi * (Do - Di) * t**2)
    sigma2 = 0.0 if F2_single == 0 else (4.0 * abs(F2_single) * Dm) / (math.pi * (Do - Di) * t**2)
    pct = (smax_single / h0) * 100.0
    note_corsa = (
        "ATTENZIONE: corsa singola oltre h0 (possibile appiattimento)"
        if smax_single > h0
        else "Corsa singola nel campo elastico"
    )

    if n_series == 1 and n_parallel == 1:
        cfg_txt = "Singola"
    elif n_series > 1 and n_parallel == 1:
        cfg_txt = f"Serie ({n_series})"
    elif n_series == 1 and n_parallel > 1:
        cfg_txt = f"Parallelo ({n_parallel})"
    else:
        cfg_txt = f"Mista serie/parallelo ({n_series}x{n_parallel})"

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale", mat.name),
        ("Modo calcolo", mode),
        ("Sorgente geometria", source),
        ("Molla tazza standard", std.name if std is not None else "-"),
        ("Diametro esterno Do", _v(Do, "mm")),
        ("Diametro interno Di", _v(Di, "mm")),
        ("Spessore t", _v(t, "mm")),
        ("Altezza conica h0", _v(h0, "mm")),
        ("Diametro medio Dm", _v(Dm, "mm")),
        _section_row("CONDIZIONI DI LAVORO"),
        ("Modulo elastico E", _v(E, "MPa")),
        ("Configurazione", cfg_txt),
        ("Numero in serie", _v(n_series)),
        ("Numero in parallelo", _v(n_parallel)),
        ("Rigidezza singola", _v(k_single, "N/mm")),
        ("Rigidezza equivalente", _v(k_eq, "N/mm")),
        ("Poisson nu", _v(nu, digits=4)),
        ("Corsa massima pacco smax", _v(smax, "mm")),
        ("Corsa massima singola", _v(smax_single, "mm")),
        ("Utilizzo corsa max singola", _v(pct, "%")),
        ("Forza massima lavoro pacco Fmax", _v(Fmax, "N")),
        ("Forza massima su singola", _v(Fmax_single, "N")),
        _section_row("DATI PUNTI DI LAVORO"),
        *_work_points_rows(f1, F1, f2, F2, "mm"),
        ("f1 singola", _v(s1_single, "mm")),
        ("F1 singola", _v(F1_single, "N")),
        ("f2 singola", _v(s2_single, "mm")),
        ("F2 singola", _v(F2_single, "N")),
        ("Sigma punto 1", _v(sigma1, "MPa")),
        ("Sigma punto 2", _v(sigma2, "MPa")),
        _section_row("VERIFICA MATERIALE"),
        ("Tensione max sigma (singola)", _v(sigma, "MPa")),
        ("Nota corsa", note_corsa),
    ]
    rows.extend(_stress_check_rows("Sigma", sigma, sigma_amm))
    if notes:
        rows.append(("Note punti lavoro", " | ".join(notes)))
    return rows


def _beam_is_pinned(s: str) -> bool:
    return s in BEAM_SUPPORT_PINNED


def _beam_validate_supports(sx: str, dx: str) -> str:
    if sx == BEAM_SUPPORT_FREE and dx == BEAM_SUPPORT_FREE:
        raise ValueError("Configurazione non valida: LIBERA - LIBERA.")
    if (sx == BEAM_SUPPORT_FREE and _beam_is_pinned(dx)) or (_beam_is_pinned(sx) and dx == BEAM_SUPPORT_FREE):
        raise ValueError("Configurazione instabile: una estremita libera e l'altra solo appoggiata/incernierata.")
    if _beam_is_pinned(sx) and _beam_is_pinned(dx):
        return "APPOGGIATA-APPOGGIATA"
    if sx == BEAM_SUPPORT_FIXED and dx == BEAM_SUPPORT_FREE:
        return "INCASTRATA-LIBERA"
    if sx == BEAM_SUPPORT_FREE and dx == BEAM_SUPPORT_FIXED:
        return "LIBERA-INCASTRATA"
    raise ValueError("Configurazione vincoli iperstatica/non gestita in questa versione.")


def _cumtrapz(x_vals: Sequence[float], y_vals: Sequence[float]) -> list[float]:
    n = min(len(x_vals), len(y_vals))
    if n == 0:
        return []
    out = [0.0]
    for i in range(1, n):
        dx = x_vals[i] - x_vals[i - 1]
        area = 0.5 * (y_vals[i] + y_vals[i - 1]) * dx
        out.append(out[-1] + area)
    return out


def _beam_distributed_at(
    x: float,
    L: float,
    q_total: float,
    distributed_loads: Sequence[tuple[float, float, float]],
) -> float:
    w = q_total / L if L > 0 else 0.0
    for n_tot, x1, x2 in distributed_loads:
        if x >= x1 and x <= x2:
            w += n_tot / (x2 - x1)
    return w


def _beam_simply_supported_diagrams(
    L: float,
    E: float,
    I: float,
    q_total: float,
    point_loads: Sequence[tuple[float, float]],
    distributed_loads: Sequence[tuple[float, float, float]],
    n_points: int = 240,
) -> tuple[list[float], list[float], list[float], list[float], float, float]:
    EI = E * I
    if EI <= 0:
        raise ValueError("Prodotto E*I non valido.")

    step = L / (n_points - 1)
    x_vals = [i * step for i in range(n_points)]
    w_vals = [_beam_distributed_at(x, L, q_total, distributed_loads) for x in x_vals]
    w_int = _cumtrapz(x_vals, w_vals)
    wx_int = _cumtrapz(x_vals, [w * x for w, x in zip(w_vals, x_vals)])

    w_tot = w_int[-1]
    mw_tot = wx_int[-1]
    p_tot = sum(P for P, _x in point_loads)
    mp_tot = sum(P * x for P, x in point_loads)
    rb = 0.0 if L <= 0 else (mw_tot + mp_tot) / L
    ra = (w_tot + p_tot) - rb

    v_vals: list[float] = []
    m_vals: list[float] = []
    for i, x in enumerate(x_vals):
        w_left = w_int[i]
        wx_left = wx_int[i]
        p_left = sum(P for P, xp in point_loads if xp <= x)
        mp_left = sum(P * (x - xp) for P, xp in point_loads if xp <= x)
        v_vals.append(ra - w_left - p_left)
        m_vals.append((ra * x) - ((x * w_left) - wx_left) - mp_left)

    curv_vals = [m / EI for m in m_vals]
    theta0 = _cumtrapz(x_vals, curv_vals)
    y0 = _cumtrapz(x_vals, theta0)
    c1 = -(y0[-1] / L) if L > 0 else 0.0
    y_vals = [y + (c1 * x) for y, x in zip(y0, x_vals)]
    return x_vals, v_vals, m_vals, y_vals, ra, rb


def _beam_cantilever_diagrams_left_fixed(
    L: float,
    E: float,
    I: float,
    q_total: float,
    point_loads: Sequence[tuple[float, float]],
    distributed_loads: Sequence[tuple[float, float, float]],
    n_points: int = 240,
) -> tuple[list[float], list[float], list[float], list[float], float, float]:
    EI = E * I
    if EI <= 0:
        raise ValueError("Prodotto E*I non valido.")

    step = L / (n_points - 1)
    x_vals = [i * step for i in range(n_points)]
    w_vals = [_beam_distributed_at(x, L, q_total, distributed_loads) for x in x_vals]
    w_int = _cumtrapz(x_vals, w_vals)
    wx_int = _cumtrapz(x_vals, [w * x for w, x in zip(w_vals, x_vals)])
    w_tot = w_int[-1]
    wx_tot = wx_int[-1]

    v_vals: list[float] = []
    m_vals: list[float] = []
    for i, x in enumerate(x_vals):
        w_left = w_int[i]
        wx_left = wx_int[i]
        w_right = w_tot - w_left
        wx_right = wx_tot - wx_left
        p_right = sum(P for P, xp in point_loads if xp >= x)
        mp_right = sum(P * (xp - x) for P, xp in point_loads if xp >= x)
        v_vals.append(-w_right - p_right)
        m_vals.append(-((wx_right - (x * w_right)) + mp_right))

    curv_vals = [m / EI for m in m_vals]
    theta_vals = _cumtrapz(x_vals, curv_vals)
    y_vals = _cumtrapz(x_vals, theta_vals)

    r_fixed = w_tot + sum(P for P, _x in point_loads)
    m_fixed = wx_tot + sum(P * x for P, x in point_loads)
    return x_vals, v_vals, m_vals, y_vals, r_fixed, m_fixed


def calc_beam_bending_advanced(
    values: dict[str, CalcValue],
    point_loads: Sequence[tuple[float, float]],
    distributed_loads: Sequence[tuple[float, float, float]] | None = None,
) -> tuple[CalcRows, dict[str, list[float]]]:
    mat, E, _G, sigma_amm, _tau_amm = _beam_material_values(values)
    L = float(values["L"])
    q_total = float(values.get("q_total", 0.0))
    sx = str(values["vincolo_sx"]).strip().upper()
    dx = str(values["vincolo_dx"]).strip().upper()

    _require_gt_zero("Lunghezza trave L", L)
    _require_gt_zero("Modulo elastico E", E)

    sec_type, area, inertia, w_res, sec_desc = _beam_section_properties(values)
    _require_gt_zero("Inerzia sezione I", inertia)
    _require_gt_zero("Modulo resistente W", w_res)

    clean_loads: list[tuple[float, float]] = []
    for idx, (P, xp) in enumerate(point_loads, start=1):
        if xp < 0 or xp > L:
            raise ValueError(f"Carico puntuale {idx}: posizione fuori trave (0..L).")
        if abs(P) > 0.0:
            clean_loads.append((P, xp))

    clean_distributed: list[tuple[float, float, float]] = []
    if distributed_loads:
        for idx, (n_tot, x1, x2) in enumerate(distributed_loads, start=1):
            if x1 < 0 or x2 < 0 or x1 > L or x2 > L:
                raise ValueError(f"Distribuito {idx}: estremi fuori trave (0..L).")
            if x2 <= x1:
                raise ValueError(f"Distribuito {idx}: distanza fine deve essere > distanza inizio.")
            if abs(n_tot) > 0.0:
                clean_distributed.append((n_tot, x1, x2))

    model = _beam_validate_supports(sx, dx)
    if model == "APPOGGIATA-APPOGGIATA":
        x_vals, v_vals, m_vals, y_vals, r1, r2 = _beam_simply_supported_diagrams(
            L,
            E,
            inertia,
            q_total,
            clean_loads,
            clean_distributed,
        )
        reac_rows = [("Reazione sx", _v(r1, "N")), ("Reazione dx", _v(r2, "N"))]
    elif model == "INCASTRATA-LIBERA":
        x_vals, v_vals, m_vals, y_vals, r1, m1 = _beam_cantilever_diagrams_left_fixed(
            L,
            E,
            inertia,
            q_total,
            clean_loads,
            clean_distributed,
        )
        reac_rows = [("Reazione incastro sx", _v(r1, "N")), ("Momento incastro sx", _v(m1, "Nmm"))]
    elif model == "LIBERA-INCASTRATA":
        mirrored = [(P, L - xp) for P, xp in clean_loads]
        mirrored_dist = [(n, L - x2, L - x1) for n, x1, x2 in clean_distributed]
        x_loc, v_loc, m_loc, y_loc, r2, m2 = _beam_cantilever_diagrams_left_fixed(
            L,
            E,
            inertia,
            q_total,
            mirrored,
            mirrored_dist,
        )
        x_vals = [L - x for x in reversed(x_loc)]
        v_vals = list(reversed(v_loc))
        m_vals = list(reversed(m_loc))
        y_vals = list(reversed(y_loc))
        reac_rows = [("Reazione incastro dx", _v(r2, "N")), ("Momento incastro dx", _v(m2, "Nmm"))]
    else:
        raise ValueError("Modello vincoli non disponibile.")

    m_max = max((abs(m) for m in m_vals), default=0.0)
    v_max = max((abs(v) for v in v_vals), default=0.0)
    y_max = max((abs(y) for y in y_vals), default=0.0)
    sigma = 0.0 if m_max == 0 else m_max / w_res
    n_tot_zones = sum(n for n, _x1, _x2 in clean_distributed)
    q_tot_all = q_total + n_tot_zones
    k_eq_load = max((abs(P) for P, _x in clean_loads), default=0.0) + abs(q_tot_all)
    k_eq = float("inf") if y_max <= 1e-12 else k_eq_load / y_max

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale trave", mat.name),
        ("Schema vincoli", f"{sx} - {dx}"),
        ("Tipo sezione", sec_type),
        ("Sezione", sec_desc),
        ("Area A", _v(area, "mm^2")),
        ("Momento inerzia I", _v(inertia, "mm^4")),
        ("Modulo resistente W", _v(w_res, "mm^3")),
        ("Lunghezza trave L", _v(L, "mm")),
        _section_row("CARICHI"),
        ("Carichi distribuiti zonali tot.", _v(n_tot_zones, "N")),
        ("Carico distribuito equivalente", _v(n_tot_zones / L if L > 0 else 0.0, "N/mm")),
        ("Numero carichi puntuali", _v(len(clean_loads))),
        ("Numero distribuiti zonali", _v(len(clean_distributed))),
        _section_row("RISULTATI"),
        ("Taglio massimo |V|max", _v(v_max, "N")),
        ("Momento massimo |M|max", _v(m_max, "Nmm")),
        ("Freccia massima |y|max", _v(y_max, "mm")),
        ("Tensione flessione sigma", _v(sigma, "MPa")),
        ("Rigidezza equivalente", _v(k_eq, "N/mm") if math.isfinite(k_eq) else "infinita"),
    ]
    rows.extend(reac_rows)
    rows.extend(_stress_check_rows("Sigma", sigma, sigma_amm))
    if not clean_loads and q_tot_all == 0:
        rows.append(("Note", "Nessun carico applicato."))

    diagrams = {"x": x_vals, "V": v_vals, "M": m_vals, "y": y_vals}
    return rows, diagrams


def _beam_validate_torsion_supports(sx: str, dx: str) -> str:
    sx_u = sx.strip().upper()
    dx_u = dx.strip().upper()
    if sx_u == BEAM_SUPPORT_FIXED and dx_u == BEAM_SUPPORT_FREE:
        return "INCASTRATA-LIBERA"
    if sx_u == BEAM_SUPPORT_FREE and dx_u == BEAM_SUPPORT_FIXED:
        return "LIBERA-INCASTRATA"
    if sx_u == BEAM_SUPPORT_FIXED and dx_u == BEAM_SUPPORT_FIXED:
        return "INCASTRATA-INCASTRATA"
    raise ValueError(
        "Per torsione sono ammessi solo: INCASTRATA-LIBERA, LIBERA-INCASTRATA, INCASTRATA-INCASTRATA."
    )


def _torsion_distributed_at(
    x: float,
    L: float,
    mt_total: float,
    distributed_torques: Sequence[tuple[float, float, float]],
) -> float:
    mt = mt_total / L if L > 0 else 0.0
    for mt_tot, x1, x2 in distributed_torques:
        if x >= x1 and x <= x2:
            mt += mt_tot / (x2 - x1)
    return mt


def _beam_torsion_left_applied(
    L: float,
    mt_total: float,
    point_torques: Sequence[tuple[float, float]],
    distributed_torques: Sequence[tuple[float, float, float]],
    n_points: int = 240,
) -> tuple[list[float], list[float], float]:
    step = L / (n_points - 1)
    x_vals = [i * step for i in range(n_points)]
    mt_vals = [_torsion_distributed_at(x, L, mt_total, distributed_torques) for x in x_vals]
    mt_int = _cumtrapz(x_vals, mt_vals)

    left_applied: list[float] = []
    for i, x in enumerate(x_vals):
        m_left = mt_int[i]
        p_left = sum(M for M, xm in point_torques if xm <= x)
        left_applied.append(m_left + p_left)

    total_external = mt_int[-1] + sum(M for M, _x in point_torques)
    return x_vals, left_applied, total_external


def _beam_torsion_left_fixed_diagrams(
    L: float,
    G: float,
    J: float,
    mt_total: float,
    point_torques: Sequence[tuple[float, float]],
    distributed_torques: Sequence[tuple[float, float, float]],
) -> tuple[list[float], list[float], list[float], float]:
    _require_gt_zero("Prodotto G*J", G * J)
    x_vals, left_applied, total_external = _beam_torsion_left_applied(
        L, mt_total, point_torques, distributed_torques
    )
    r_fixed = -total_external
    t_vals = [r_fixed + m for m in left_applied]
    theta_rad = _cumtrapz(x_vals, [t / (G * J) for t in t_vals])
    return x_vals, t_vals, theta_rad, r_fixed


def _beam_torsion_fixed_fixed_diagrams(
    L: float,
    G: float,
    J: float,
    mt_total: float,
    point_torques: Sequence[tuple[float, float]],
    distributed_torques: Sequence[tuple[float, float, float]],
) -> tuple[list[float], list[float], list[float], float, float]:
    _require_gt_zero("Prodotto G*J", G * J)
    x_vals, left_applied, total_external = _beam_torsion_left_applied(
        L, mt_total, point_torques, distributed_torques
    )
    int_left = _cumtrapz(x_vals, left_applied)[-1]
    r_sx = -(int_left / L) if L > 0 else 0.0
    r_dx = -(r_sx + total_external)
    t_vals = [r_sx + m for m in left_applied]
    theta_raw = _cumtrapz(x_vals, [t / (G * J) for t in t_vals])
    drift = theta_raw[-1] if theta_raw else 0.0
    theta_rad = [th - ((x / L) * drift if L > 0 else 0.0) for th, x in zip(theta_raw, x_vals)]
    return x_vals, t_vals, theta_rad, r_sx, r_dx


def calc_beam_torsion_advanced(
    values: dict[str, CalcValue],
    point_torques: Sequence[tuple[float, float]],
    distributed_torques: Sequence[tuple[float, float, float]] | None = None,
) -> tuple[CalcRows, dict[str, list[float]]]:
    mat, _E, G, _sigma_amm, tau_amm = _beam_material_values(values)
    L = float(values["L"])
    sec_type, area, j_t, r_max, sec_desc = _beam_torsion_section_properties(values)
    mt_total_nm = float(values.get("mt_total", 0.0))
    sx = str(values["vincolo_sx"]).strip().upper()
    dx = str(values["vincolo_dx"]).strip().upper()

    _require_gt_zero("Lunghezza trave L", L)
    _require_gt_zero("Modulo di taglio G", G)
    _require_gt_zero("Costante torsionale Jt", j_t)
    _require_gt_zero("Raggio equivalente r", r_max)

    clean_point_nm: list[tuple[float, float]] = []
    for idx, (m_nm, xm) in enumerate(point_torques, start=1):
        if xm < 0 or xm > L:
            raise ValueError(f"Momento torcente puntuale {idx}: posizione fuori trave (0..L).")
        if abs(m_nm) > 0.0:
            clean_point_nm.append((m_nm, xm))

    clean_dist_nm: list[tuple[float, float, float]] = []
    if distributed_torques:
        for idx, (m_tot_nm, x1, x2) in enumerate(distributed_torques, start=1):
            if x1 < 0 or x2 < 0 or x1 > L or x2 > L:
                raise ValueError(f"Distribuito torsione {idx}: estremi fuori trave (0..L).")
            if x2 <= x1:
                raise ValueError(f"Distribuito torsione {idx}: distanza fine deve essere > distanza inizio.")
            if abs(m_tot_nm) > 0.0:
                clean_dist_nm.append((m_tot_nm, x1, x2))

    mt_total_nmm = mt_total_nm * 1000.0
    clean_point_nmm = [(m_nm * 1000.0, xm) for m_nm, xm in clean_point_nm]
    clean_dist_nmm = [(m_tot_nm * 1000.0, x1, x2) for m_tot_nm, x1, x2 in clean_dist_nm]

    model = _beam_validate_torsion_supports(sx, dx)
    if model == "INCASTRATA-LIBERA":
        x_vals, t_vals, theta_rad_vals, r_sx = _beam_torsion_left_fixed_diagrams(
            L, G, j_t, mt_total_nmm, clean_point_nmm, clean_dist_nmm
        )
        reac_rows = [("Reazione torsionale incastro sx", _v(r_sx / 1000.0, "Nm"))]
    elif model == "LIBERA-INCASTRATA":
        mirrored_point = [(m, L - xm) for m, xm in clean_point_nmm]
        mirrored_dist = [(m, L - x2, L - x1) for m, x1, x2 in clean_dist_nmm]
        x_loc, t_loc, theta_loc, r_dx = _beam_torsion_left_fixed_diagrams(
            L, G, j_t, mt_total_nmm, mirrored_point, mirrored_dist
        )
        x_vals = [L - x for x in reversed(x_loc)]
        t_vals = list(reversed(t_loc))
        theta_rad_vals = list(reversed(theta_loc))
        reac_rows = [("Reazione torsionale incastro dx", _v(r_dx / 1000.0, "Nm"))]
    else:  # INCASTRATA-INCASTRATA
        x_vals, t_vals, theta_rad_vals, r_sx, r_dx = _beam_torsion_fixed_fixed_diagrams(
            L, G, j_t, mt_total_nmm, clean_point_nmm, clean_dist_nmm
        )
        reac_rows = [
            ("Reazione torsionale sx", _v(r_sx / 1000.0, "Nm")),
            ("Reazione torsionale dx", _v(r_dx / 1000.0, "Nm")),
        ]

    theta_deg_vals = [math.degrees(th) for th in theta_rad_vals]
    t_max_nmm = max((abs(t) for t in t_vals), default=0.0)
    theta_max_deg = max((abs(th) for th in theta_deg_vals), default=0.0)
    theta_max_rad = max((abs(th) for th in theta_rad_vals), default=0.0)
    tau_max = 0.0 if t_max_nmm == 0 else (t_max_nmm * r_max) / j_t

    n_tot_dist_nm = sum(m for m, _x1, _x2 in clean_dist_nm)
    mt_tot_all_nm = mt_total_nm + n_tot_dist_nm
    theta_tip_deg = abs(theta_deg_vals[-1] - theta_deg_vals[0]) if len(theta_deg_vals) >= 2 else 0.0

    rows: CalcRows = [
        _section_row("DATI DIMENSIONALI"),
        ("Materiale trave", mat.name),
        ("Schema vincoli", f"{sx} - {dx}"),
        ("Tipo sezione", sec_type),
        ("Sezione", sec_desc),
        ("Area A", _v(area, "mm^2")),
        ("Lunghezza trave L", _v(L, "mm")),
        ("Costante torsionale Jt", _v(j_t, "mm^4")),
        ("Raggio equivalente r", _v(r_max, "mm")),
        _section_row("CARICHI"),
        ("Momento torcente distribuito base", _v(mt_total_nm, "Nm")),
        ("Momenti torcenti distribuiti zonali tot.", _v(n_tot_dist_nm, "Nm")),
        ("Momento torcente totale complessivo", _v(mt_tot_all_nm, "Nm")),
        ("Momento distribuito equivalente", _v(mt_tot_all_nm / L if L > 0 else 0.0, "Nm/mm")),
        ("Numero momenti puntuali", _v(len(clean_point_nm))),
        ("Numero distribuiti zonali", _v(len(clean_dist_nm))),
        _section_row("RISULTATI"),
        ("Momento torcente interno massimo |T|max", _v(t_max_nmm / 1000.0, "Nm")),
        ("Tensione tangenziale massima tau", _v(tau_max, "MPa")),
        ("Angolo torsione massimo |theta|max", _v(theta_max_deg, "gradi")),
        ("Angolo torsione massimo |theta|max", _v(theta_max_rad, "rad")),
        ("Rotazione relativa estremi |delta theta|", _v(theta_tip_deg, "gradi")),
    ]
    rows.extend(reac_rows)
    rows.extend(_stress_check_rows("Tau", tau_max, tau_amm))
    if not clean_point_nm and mt_tot_all_nm == 0:
        rows.append(("Note", "Nessun momento torcente applicato."))

    diagrams = {"x": x_vals, "T": [t / 1000.0 for t in t_vals], "theta_deg": theta_deg_vals}
    return rows, diagrams


def calc_beam_bending(values: dict[str, float | int | str]) -> CalcRows:
    F = float(values["F"])
    L = float(values["L"])
    I = float(values["I"])
    W = float(values["W"])
    mat, E, _G, sigma_amm, _tau_amm = _beam_material_values(values)

    _require_ge_zero("Carico F", F)
    _require_gt_zero("Luce trave L", L)
    _require_gt_zero("Modulo elastico E", E)
    _require_gt_zero("Momento di inerzia I", I)
    _require_gt_zero("Modulo resistente W", W)

    Mmax = (F * L) / 4.0
    sigma = 0.0 if F == 0 else Mmax / W
    y = 0.0 if F == 0 else (F * L**3) / (48.0 * E * I)
    k = float("inf") if y == 0 else F / y

    rows: CalcRows = [
        ("Materiale trave", mat.name),
        ("Momento flettente massimo Mmax", _v(Mmax, "Nmm")),
        ("Tensione di flessione sigma", _v(sigma, "MPa")),
        ("Freccia massima y", _v(y, "mm")),
        ("Rigidezza globale k", _v(k, "N/mm") if math.isfinite(k) else "infinita"),
        ("Schema", "Trave appoggiata con carico concentrato in mezzeria"),
    ]
    rows.extend(_stress_check_rows("Sigma", sigma, sigma_amm))
    return rows


def calc_beam_torsion(values: dict[str, float | int | str]) -> CalcRows:
    T_nm = float(values["T"])
    L = float(values["L"])
    J = float(values["J"])
    r = float(values["r"])
    mat, _E, G, _sigma_amm, tau_amm = _beam_material_values(values)

    _require_ge_zero("Momento torcente T", T_nm)
    _require_gt_zero("Lunghezza L", L)
    _require_gt_zero("Modulo di taglio G", G)
    _require_gt_zero("Momento polare J", J)
    _require_gt_zero("Raggio esterno r", r)

    T_nmm = T_nm * 1000.0
    tau = 0.0 if T_nmm == 0 else (T_nmm * r) / J
    theta_rad = 0.0 if T_nmm == 0 else (T_nmm * L) / (G * J)
    theta_deg = math.degrees(theta_rad)

    rows: CalcRows = [
        ("Materiale trave", mat.name),
        ("Tensione tangenziale tau", _v(tau, "MPa")),
        ("Angolo torsione theta", _v(theta_deg, "gradi")),
        ("Angolo torsione theta", _v(theta_rad, "rad")),
    ]
    rows.extend(_stress_check_rows("Tau", tau, tau_amm))
    return rows


def calc_tolerance_fit_iso_thermal(
    values: dict[str, CalcValue],
) -> tuple[CalcRows, dict[str, float]]:
    d_nom = float(values["d_nom"])
    hole_iso = str(values.get("hole_iso") or "").strip()
    shaft_iso = str(values.get("shaft_iso") or "").strip()
    if not hole_iso:
        hole_pos = str(values.get("hole_pos") or "").strip()
        hole_it = str(values.get("hole_it") or "").strip()
        if not hole_pos or not hole_it:
            raise ValueError("Compila posizione tolleranza e grado qualita per il foro.")
        hole_iso = f"{hole_pos}{hole_it}"
    if not shaft_iso:
        shaft_pos = str(values.get("shaft_pos") or "").strip()
        shaft_it = str(values.get("shaft_it") or "").strip()
        if not shaft_pos or not shaft_it:
            raise ValueError("Compila posizione tolleranza e grado qualita per l'albero.")
        shaft_iso = f"{shaft_pos}{shaft_it}"
    mat_hole_name = str(values["mat_hole"]).strip()
    mat_shaft_name = str(values["mat_shaft"]).strip()
    temp_c = float(values["temp_c"])

    _require_gt_zero("Diametro nominale", d_nom)

    mat_hole = _tol_material(mat_hole_name)
    mat_shaft = _tol_material(mat_shaft_name)
    zone_hole = _tol_iso_zone("HOLE", hole_iso, d_nom)
    zone_shaft = _tol_iso_zone("SHAFT", shaft_iso, d_nom)

    hole_min_20 = d_nom + (zone_hole.lower_dev_um / 1000.0)
    hole_max_20 = d_nom + (zone_hole.upper_dev_um / 1000.0)
    shaft_min_20 = d_nom + (zone_shaft.lower_dev_um / 1000.0)
    shaft_max_20 = d_nom + (zone_shaft.upper_dev_um / 1000.0)

    j_min_20 = hole_min_20 - shaft_max_20
    j_max_20 = hole_max_20 - shaft_min_20

    def _fit_type(j_min: float, j_max: float) -> str:
        if j_min > 0:
            return "Gioco"
        if j_max < 0:
            return "Interferenza"
        return "Transizione (gioco + interferenza)"

    def _state(delta: float) -> str:
        return "Gioco" if delta >= 0 else "Interferenza"

    def _limit_text(delta: float) -> str:
        if delta >= 0:
            return f"Gioco {_v(delta, 'mm', digits=6)}"
        return f"Interferenza {_v(abs(delta), 'mm', digits=6)}"

    fit_20 = _fit_type(j_min_20, j_max_20)

    dt = temp_c - 20.0
    alpha_hole = mat_hole.alpha_um_mk * 1e-6
    alpha_shaft = mat_shaft.alpha_um_mk * 1e-6

    hole_min_t = hole_min_20 * (1.0 + (alpha_hole * dt))
    hole_max_t = hole_max_20 * (1.0 + (alpha_hole * dt))
    shaft_min_t = shaft_min_20 * (1.0 + (alpha_shaft * dt))
    shaft_max_t = shaft_max_20 * (1.0 + (alpha_shaft * dt))

    j_min_t = hole_min_t - shaft_max_t
    j_max_t = hole_max_t - shaft_min_t
    fit_t = _fit_type(j_min_t, j_max_t)

    rows: CalcRows = [
        _section_row("INPUT"),
        ("Diametro nominale d", _v(d_nom, "mm")),
        ("Classe ISO foro", hole_iso),
        ("Classe ISO albero", shaft_iso),
        ("Materiale foro", mat_hole.name),
        ("Materiale albero", mat_shaft.name),
        ("Temperatura riferimento", "20 gradiC"),
        ("Temperatura esercizio", _v(temp_c, "gradiC")),
        _section_row("DEVIAZIONI ISO (um)"),
        ("Foro EI / ES", f"{_fmt_number(zone_hole.lower_dev_um)} / {_fmt_number(zone_hole.upper_dev_um)} um"),
        ("Albero ei / es", f"{_fmt_number(zone_shaft.lower_dev_um)} / {_fmt_number(zone_shaft.upper_dev_um)} um"),
        _section_row("RIFERIMENTO 20 gradiC"),
        ("Foro min @20C", _v(hole_min_20, "mm", digits=6)),
        ("Foro max @20C", _v(hole_max_20, "mm", digits=6)),
        ("Albero min @20C", _v(shaft_min_20, "mm", digits=6)),
        ("Albero max @20C", _v(shaft_max_20, "mm", digits=6)),
        ("Delta min @20C", _v(j_min_20, "mm", digits=6)),
        ("Delta max @20C", _v(j_max_20, "mm", digits=6)),
        ("Esito limite min @20C", _limit_text(j_min_20)),
        ("Esito limite max @20C", _limit_text(j_max_20)),
        ("Stato limite min @20C", _state(j_min_20)),
        ("Stato limite max @20C", _state(j_max_20)),
        ("Tipo accoppiamento @20C", fit_20),
        _section_row("ESERCIZIO TERMICO"),
        ("Alpha foro", _v(mat_hole.alpha_um_mk, "um/(m*K)")),
        ("Alpha albero", _v(mat_shaft.alpha_um_mk, "um/(m*K)")),
        ("Foro min @T", _v(hole_min_t, "mm", digits=6)),
        ("Foro max @T", _v(hole_max_t, "mm", digits=6)),
        ("Albero min @T", _v(shaft_min_t, "mm", digits=6)),
        ("Albero max @T", _v(shaft_max_t, "mm", digits=6)),
        ("Delta min @T", _v(j_min_t, "mm", digits=6)),
        ("Delta max @T", _v(j_max_t, "mm", digits=6)),
        ("Esito limite min @T", _limit_text(j_min_t)),
        ("Esito limite max @T", _limit_text(j_max_t)),
        ("Stato limite min @T", _state(j_min_t)),
        ("Stato limite max @T", _state(j_max_t)),
        ("Tipo accoppiamento @T", fit_t),
    ]

    graph = {
        "d_nom": d_nom,
        "temp_c": temp_c,
        "hole_min_20": hole_min_20,
        "hole_max_20": hole_max_20,
        "shaft_min_20": shaft_min_20,
        "shaft_max_20": shaft_max_20,
        "hole_min_t": hole_min_t,
        "hole_max_t": hole_max_t,
        "shaft_min_t": shaft_min_t,
        "shaft_max_t": shaft_max_t,
        "j_min_20": j_min_20,
        "j_max_20": j_max_20,
        "j_min_t": j_min_t,
        "j_max_t": j_max_t,
    }
    return rows, graph


def calc_tolerance_fit(values: dict[str, float | int | str]) -> CalcRows:
    h_min = float(values["h_min"])
    h_max = float(values["h_max"])
    s_min = float(values["s_min"])
    s_max = float(values["s_max"])

    if h_min > h_max:
        raise ValueError("Foro min non puo superare foro max.")
    if s_min > s_max:
        raise ValueError("Albero min non puo superare albero max.")

    t_h = h_max - h_min
    t_s = s_max - s_min
    j_min = h_min - s_max
    j_max = h_max - s_min

    if j_min > 0:
        fit = "Con gioco"
    elif j_max < 0:
        fit = "Con interferenza"
    else:
        fit = "Di transizione"

    return [
        ("Tolleranza foro Th", _v(t_h, "mm")),
        ("Tolleranza albero Ts", _v(t_s, "mm")),
        ("Gioco minimo Jmin", _v(j_min, "mm")),
        ("Gioco massimo Jmax", _v(j_max, "mm")),
        ("Tipo accoppiamento", fit),
    ]


def calc_tolerance_chain(values: dict[str, float | int | str]) -> CalcRows:
    op = str(values["op"])
    A = float(values["A_nom"])
    A_plus = float(values["A_plus"])
    A_minus = float(values["A_minus"])
    B = float(values["B_nom"])
    B_plus = float(values["B_plus"])
    B_minus = float(values["B_minus"])

    _require_ge_zero("A +tol", A_plus)
    _require_ge_zero("A -tol", A_minus)
    _require_ge_zero("B +tol", B_plus)
    _require_ge_zero("B -tol", B_minus)

    if op == "Somma":
        C_nom = A + B
        C_max = (A + A_plus) + (B + B_plus)
        C_min = (A - A_minus) + (B - B_minus)
    else:
        C_nom = A - B
        C_max = (A + A_plus) - (B - B_minus)
        C_min = (A - A_minus) - (B + B_plus)

    C_plus = C_max - C_nom
    C_minus = C_nom - C_min
    T = C_max - C_min

    return [
        ("Risultato nominale C", _v(C_nom, "mm")),
        ("Limite inferiore Cmin", _v(C_min, "mm")),
        ("Limite superiore Cmax", _v(C_max, "mm")),
        ("Tolleranza superiore +", _v(C_plus, "mm")),
        ("Tolleranza inferiore -", _v(C_minus, "mm")),
        ("Campo totale T", _v(T, "mm")),
    ]


GEAR_CALCS: list[tuple[str, str, Sequence[FieldSpec], CalcFn]] = [
    (
        "Cilindrici diritti",
        "Calcolo geometrico base per coppia di ingranaggi cilindrici a denti diritti.",
        (
            FieldSpec("m", "Modulo m", "2", "mm"),
            FieldSpec("z1", "Denti pignone z1", "20", field_type="int"),
            FieldSpec("z2", "Denti ruota z2", "40", field_type="int"),
            FieldSpec("alpha", "Angolo pressione alpha", "20", "gradi"),
            FieldSpec("n1", "Velocita pignone n1", "1200", "rpm"),
            FieldSpec("aw", "Interasse target aw", "", "mm", field_type="float_optional"),
            FieldSpec(
                "x_mode",
                "Ripartizione correzione x",
                GEAR_X_MODE_BOTH,
                field_type="choice",
                choices=GEAR_X_MODE_CHOICES,
            ),
        ),
        calc_gear_spur,
    ),
    (
        "Cilindrici elicoidali",
        "Geometria preliminare per ingranaggi cilindrici elicoidali.",
        (
            FieldSpec("mn", "Modulo normale mn", "2", "mm"),
            FieldSpec("beta", "Angolo elica beta", "15", "gradi"),
            FieldSpec("alpha", "Angolo pressione alpha", "20", "gradi"),
            FieldSpec("z1", "Denti pignone z1", "18", field_type="int"),
            FieldSpec("z2", "Denti ruota z2", "54", field_type="int"),
            FieldSpec("n1", "Velocita pignone n1", "1500", "rpm"),
            FieldSpec("aw", "Interasse target aw", "", "mm", field_type="float_optional"),
            FieldSpec(
                "x_mode",
                "Ripartizione correzione x",
                GEAR_X_MODE_BOTH,
                field_type="choice",
                choices=GEAR_X_MODE_CHOICES,
            ),
        ),
        calc_gear_helical,
    ),
    (
        "Conici diritti",
        "Calcolo diametri primitivi e coni di passo per coppie coniche a denti diritti.",
        (
            FieldSpec("m", "Modulo m", "3", "mm"),
            FieldSpec("z1", "Denti pignone z1", "18", field_type="int"),
            FieldSpec("z2", "Denti ruota z2", "36", field_type="int"),
            FieldSpec("sigma", "Angolo assi sigma", "90", "gradi"),
        ),
        calc_gear_bevel_spur,
    ),
    (
        "Conici elicoidali",
        "Calcolo preliminare per ingranaggi conici elicoidali (modello semplificato).",
        (
            FieldSpec("mn", "Modulo normale mn", "3", "mm"),
            FieldSpec("beta", "Angolo elica beta", "25", "gradi"),
            FieldSpec("alpha", "Angolo pressione alpha", "20", "gradi"),
            FieldSpec("z1", "Denti pignone z1", "16", field_type="int"),
            FieldSpec("z2", "Denti ruota z2", "32", field_type="int"),
            FieldSpec("sigma", "Angolo assi sigma", "90", "gradi"),
        ),
        calc_gear_bevel_helical,
    ),
    (
        "Vite senza fine",
        "Geometria base per accoppiamento vite senza fine e ruota.",
        (
            FieldSpec("m", "Modulo m", "2.5", "mm"),
            FieldSpec("z1", "Principi vite z1", "2", field_type="int"),
            FieldSpec("z2", "Denti ruota z2", "40", field_type="int"),
            FieldSpec("q", "Fattore diametrale q", "10"),
            FieldSpec("n1", "Velocita vite n1", "1400", "rpm"),
        ),
        calc_gear_worm,
    ),
    (
        "Vite madrevite",
        "Calcolo preliminare sistema vite-madrevite: forza/coppia, rendimento e verifiche.",
        (
            FieldSpec(
                "vm_thread_family",
                "Tipo filettatura",
                SCREW_THREAD_FAMILY_CHOICES[0],
                field_type="choice",
                choices=SCREW_THREAD_FAMILY_CHOICES,
            ),
            FieldSpec(
                "vm_thread_std",
                "Dimensione filettatura",
                _screw_thread_names_by_family(SCREW_THREAD_FAMILY_CHOICES[0])[0],
                field_type="choice",
                choices=SCREW_THREAD_CHOICES,
            ),
            FieldSpec("vm_d", "Diametro vite d", "20", "mm"),
            FieldSpec("vm_p", "Passo p", "4", "mm"),
            FieldSpec("vm_mu", "Attrito mu", "0.12"),
            FieldSpec(
                "vm_mat_nut",
                "Materiale madrevite",
                SCREW_MATERIAL_CHOICES[0],
                field_type="choice",
                choices=SCREW_MATERIAL_CHOICES,
            ),
            FieldSpec("vm_Le", "Lunghezza madrevite Le", "24", "mm"),
            FieldSpec(
                "vm_mat_screw",
                "Materiale vite",
                SCREW_MATERIAL_CHOICES[0],
                field_type="choice",
                choices=SCREW_MATERIAL_CHOICES,
            ),
            FieldSpec(
                "vm_mode",
                "Modo calcolo",
                SCREW_VM_MODE_FORCE_FROM_TORQUE,
                field_type="choice",
                choices=SCREW_VM_MODE_CHOICES,
            ),
            FieldSpec("vm_T", "Coppia T", "", "Nm", field_type="float_optional"),
            FieldSpec("vm_F", "Forza assiale F", "", "N", field_type="float_optional"),
        ),
        calc_power_screw,
    ),
]


def get_spring_calcs(
    material_choices: Sequence[str],
    disc_choices: Sequence[str],
) -> list[tuple[str, str, Sequence[FieldSpec], CalcFn]]:
    mat_field = _spring_material_field(material_choices)
    mat_data_fields = _spring_material_data_fields()
    work_fields = _spring_work_fields()
    torsion_work_fields = _spring_work_fields(
        SPRING_CALC_MODE_FORCE_FROM_DEF_ANG,
        deflection_label="Angolo lavoro",
        deflection_unit="°",
        f1_default="15",
        f2_default="30",
    )
    disc_options = tuple(disc_choices) if disc_choices else ("-",)
    disc_default = disc_options[0]

    return [
        (
            "Compressione sez. tonda",
            "Materiale da DB + terminali + punti lavoro f/F (anche inverso).",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec(
                    "terminale",
                    "Terminali",
                    SPRING_TERMINALS_COMPRESSION[2],
                    field_type="choice",
                    choices=SPRING_TERMINALS_COMPRESSION,
                ),
                FieldSpec("d", "Diametro filo d", "3", "mm"),
                FieldSpec("Dm", "Diametro medio Dm", "24", "mm"),
                FieldSpec("Na", "Spire attive Na", "8"),
                FieldSpec("L0", "Lunghezza libera L0", "55", "mm"),
                *work_fields,
            ),
            calc_spring_comp_round,
        ),
        (
            "Compressione sez. rettangolare",
            "Materiale da DB + terminali + punti lavoro f/F (anche inverso).",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec(
                    "terminale",
                    "Terminali",
                    SPRING_TERMINALS_COMPRESSION[2],
                    field_type="choice",
                    choices=SPRING_TERMINALS_COMPRESSION,
                ),
                FieldSpec("b", "Larghezza b", "3", "mm"),
                FieldSpec("h", "Altezza h", "2", "mm"),
                FieldSpec("Dm", "Diametro medio Dm", "22", "mm"),
                FieldSpec("Na", "Spire attive Na", "7"),
                FieldSpec("L0", "Lunghezza libera L0", "50", "mm"),
                *work_fields,
            ),
            calc_spring_comp_rect,
        ),
        (
            "Trazione sez. tonda",
            "Materiale da DB + terminali + trazione iniziale + punti lavoro f/F.",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec(
                    "terminale",
                    "Terminali",
                    SPRING_TERMINALS_TRACTION[0],
                    field_type="choice",
                    choices=SPRING_TERMINALS_TRACTION,
                ),
                FieldSpec("d", "Diametro filo d", "2.5", "mm"),
                FieldSpec("Dm", "Diametro medio Dm", "18", "mm"),
                FieldSpec("Na", "Spire attive Na", "12"),
                FieldSpec("F0", "Trazione iniziale F0", "80", "N"),
                *work_fields,
            ),
            calc_spring_extension_round,
        ),
        (
            "Torsione sez. tonda",
            "Materiale da DB + leva efficace + punti lavoro f/F equivalenti.",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec("d", "Diametro filo d", "4", "mm"),
                FieldSpec("Dm", "Diametro medio Dm", "28", "mm"),
                FieldSpec("Nb", "Spire attive Nb", "6"),
                FieldSpec("leva", "Leva efficace", "25", "mm"),
                *torsion_work_fields,
            ),
            calc_spring_torsion_round,
        ),
        (
            "Molla a lamina",
            "Materiale da DB + lamina trapezoidale + punti lavoro f/F.",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec("n", "Numero lamine n", "3", field_type="int"),
                FieldSpec("b_fixed", "Larghezza lato fisso", "35", "mm"),
                FieldSpec("b_free", "Larghezza lato libero", "25", "mm"),
                FieldSpec("t", "Spessore t", "4", "mm"),
                FieldSpec("L", "Lunghezza libera L", "220", "mm"),
                *work_fields,
            ),
            calc_spring_leaf,
        ),
        (
            "Molla a tazza",
            "Materiale da DB/standard + configurazione serie/parallelo + punti lavoro f/F.",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec(
                    "tazza_source",
                    "Sorgente geometria",
                    DISC_SPRING_SOURCE_DB,
                    field_type="choice",
                    choices=(DISC_SPRING_SOURCE_DB, DISC_SPRING_SOURCE_CUSTOM),
                ),
                FieldSpec(
                    "tazza_std",
                    "Molla tazza standard",
                    disc_default,
                    field_type="choice",
                    choices=disc_options,
                ),
                FieldSpec("Do", "Diametro esterno Do", "50", "mm"),
                FieldSpec("Di", "Diametro interno Di", "25", "mm"),
                FieldSpec("t", "Spessore t", "2", "mm"),
                FieldSpec("h0", "Altezza conica h0", "1.2", "mm"),
                FieldSpec("nu", "Poisson nu", "0.3"),
                FieldSpec("n_series", "Molle in serie", "1", field_type="int"),
                FieldSpec("n_parallel", "Molle in parallelo", "1", field_type="int"),
                *work_fields,
            ),
            calc_spring_disc,
        ),
    ]


def get_beam_calcs(material_choices: Sequence[str]) -> list[tuple[str, str, Sequence[FieldSpec], CalcFn]]:
    mat_field = _beam_material_field(material_choices)
    mat_data_fields = _beam_material_data_fields()

    return [
        (
            "Flessione",
            "Trave appoggiata con carico concentrato in mezzeria + materiale da DB travi.",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec("F", "Carico F", "2000", "N"),
                FieldSpec("L", "Luce trave L", "1000", "mm"),
                FieldSpec("I", "Momento inerzia I", "8500000", "mm^4"),
                FieldSpec("W", "Modulo resistente W", "170000", "mm^3"),
            ),
            calc_beam_bending,
        ),
        (
            "Torsione",
            "Albero/trave sollecitato a torsione + materiale da DB travi.",
            (
                mat_field,
                *mat_data_fields,
                FieldSpec("T", "Momento torcente T", "60", "Nm"),
                FieldSpec("L", "Lunghezza L", "800", "mm"),
                FieldSpec("J", "Momento polare J", "320000", "mm^4"),
                FieldSpec("r", "Raggio esterno r", "12", "mm"),
            ),
            calc_beam_torsion,
        ),
    ]


TOL_CALCS: list[tuple[str, str, Sequence[FieldSpec], CalcFn]] = [
    (
        "Accoppiamento foro/albero",
        "Valutazione del tipo di accoppiamento da limiti min/max.",
        (
            FieldSpec("h_min", "Foro min", "20.000", "mm"),
            FieldSpec("h_max", "Foro max", "20.021", "mm"),
            FieldSpec("s_min", "Albero min", "19.980", "mm"),
            FieldSpec("s_max", "Albero max", "20.000", "mm"),
        ),
        calc_tolerance_fit,
    ),
    (
        "Catena quote",
        "Calcolo worst-case su somma o differenza di due quote.",
        (
            FieldSpec("op", "Operazione", "Somma", field_type="choice", choices=("Somma", "Differenza")),
            FieldSpec("A_nom", "A nominale", "50", "mm"),
            FieldSpec("A_plus", "A +tol", "0.10", "mm"),
            FieldSpec("A_minus", "A -tol", "0.05", "mm"),
            FieldSpec("B_nom", "B nominale", "20", "mm"),
            FieldSpec("B_plus", "B +tol", "0.08", "mm"),
            FieldSpec("B_minus", "B -tol", "0.04", "mm"),
        ),
        calc_tolerance_chain,
    ),
]
