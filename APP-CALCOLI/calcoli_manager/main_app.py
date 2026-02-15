from __future__ import annotations

import tkinter as tk
from typing import Callable, Sequence
import tkinter.font as tkfont

try:
    import customtkinter as ctk
except Exception as e:
    raise SystemExit(
        "Questa app usa 'customtkinter'. Installa con:\n\n"
        "  pip install -r requirements.txt\n\n"
        f"Dettagli import: {e}"
    )
from tkinter import messagebox
from tkinter import ttk

from .config import APP_NAME, APP_VERSION
from .my_style_01.style import Palette, STYLE_NAME, apply_style
from .calculation_engine import (
    BEAM_DB,
    BEAM_MAT_FIELD_KEYS,
    BEAM_SECTION_RECT,
    BEAM_SECTION_RECT_TUBE,
    BEAM_SECTION_ROUND,
    BEAM_SECTION_STD,
    BEAM_TORSION_SECTION_TYPES,
    BEAM_SECTION_TUBE,
    BEAM_SECTION_TYPES,
    BEAM_SUPPORT_CHOICES,
    TOL_DB,
    DISC_SPRING_SOURCE_DB,
    GEAR_CALCS,
    SCREW_DB,
    SCREW_THREAD_FAMILY_CHOICES,
    SCREW_VM_MODE_FORCE_FROM_TORQUE,
    SCREW_VM_MODE_TORQUE_FROM_FORCE,
    SPRING_CALC_MODE_DEF_FROM_FORCE,
    SPRING_DB,
    SPRING_MAT_FIELD_KEYS,
    TOL_CALCS,
    CalcFn,
    CalcRows,
    CalcValue,
    FieldSpec,
    _as_float,
    _as_int,
    _beam_material,
    _beam_section_std,
    calc_beam_bending_advanced,
    calc_beam_torsion_advanced,
    calc_tolerance_fit_iso_thermal,
    _disc_spring_standard,
    _fmt_number,
    _screw_thread_names_by_family,
    _screw_thread_standard,
    _spring_material,
    get_beam_calcs,
    get_spring_calcs,
)

GEAR_TAB_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Cilindrici",
        (
            ("Diritti", "Cilindrici diritti"),
            ("Elicoidali", "Cilindrici elicoidali"),
        ),
    ),
    (
        "Conici",
        (
            ("Diritti", "Conici diritti"),
            ("Elicoidali", "Conici elicoidali"),
        ),
    ),
)
GEAR_GROUPED_TITLES = {calc_title for _group_title, group_tabs in GEAR_TAB_GROUPS for _tab_label, calc_title in group_tabs}
GEAR_PANEL_TITLES = GEAR_GROUPED_TITLES | {"Vite senza fine"}
SCREW_NUT_PANEL_TITLE = "Vite madrevite"


def _parse_first_number(text: str) -> float | None:
    token = (text or "").strip().split(" ", 1)[0].replace(",", ".")
    try:
        return float(token)
    except Exception:
        return None


def _result_line_tag(label: str, value_txt: str) -> str:
    label_l = (label or "").strip().lower()
    value_u = (value_txt or "").strip().upper()
    if "NON OK" in value_u:
        return "err_line"
    if value_u == "OK" or value_u.startswith("OK "):
        return "ok_line"
    if label_l.startswith("sf "):
        sf_val = _parse_first_number(value_txt)
        if sf_val is None:
            return ""
        return "ok_line" if sf_val >= 1.0 else "err_line"
    return ""


def _render_results_colored(textbox: ctk.CTkTextbox, rows: CalcRows, palette: Palette) -> None:
    textbox.configure(state="normal")
    textbox.delete("1.0", "end")
    textbox.tag_config("ok_line", foreground=palette.ok)
    textbox.tag_config("err_line", foreground=palette.err)
    for label, value in rows:
        value_txt = str(value or "").strip()
        if not value_txt:
            textbox.insert("end", f"\n{label}\n")
            continue
        line = f"{label}: {value}\n"
        tag = _result_line_tag(label, value_txt)
        if tag:
            textbox.insert("end", line, tag)
        else:
            textbox.insert("end", line)
    textbox.configure(state="disabled")


class BeamBendingPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        palette: Palette,
        beam_material_names: Sequence[str],
        beam_section_names: Sequence[str],
    ) -> None:
        super().__init__(master)
        self.palette = palette
        self.beam_material_names = tuple(beam_material_names)
        self.beam_section_names = tuple(beam_section_names) if beam_section_names else ("-",)

        self.vars: dict[str, ctk.StringVar] = {}
        self.widgets: dict[str, ctk.CTkBaseClass] = {}
        self.input_labels: dict[str, ctk.CTkLabel] = {}
        self.unit_labels: dict[str, ctk.CTkLabel] = {}
        self.base_label_texts: dict[str, str] = {}
        self.defaults: dict[str, str] = {}
        self.diagram_data: dict[str, list[float]] | None = None
        self.var_status = ctk.StringVar(value="Inserisci dati trave, carichi e premi CALCOLA.")
        self.var_std_section_info = ctk.StringVar(value="")
        self.var_new_p = ctk.StringVar(value="1000")
        self.var_new_x = ctk.StringVar(value="500")
        self.var_new_qn = ctk.StringVar(value="2000")
        self.var_new_qx1 = ctk.StringVar(value="200")
        self.var_new_qx2 = ctk.StringVar(value="800")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def _configure_load_tables_style(self) -> str:
        style_name = "BeamLoads.Treeview"
        style = ttk.Style(self)
        base = tkfont.nametofont("TkDefaultFont")
        family = str(base.cget("family"))
        base_size = abs(int(base.cget("size")))
        txt_size = max(12, base_size + 2)
        style.configure(style_name, font=(family, txt_size), rowheight=max(28, txt_size + 14))
        style.configure(f"{style_name}.Heading", font=(family, txt_size, "bold"))
        return style_name

    def _add_field(
        self,
        parent,
        key: str,
        label: str,
        default: str = "",
        unit: str = "",
        row: int = 0,
        col_base: int = 0,
        choices: Sequence[str] | None = None,
    ) -> None:
        self.defaults[key] = default
        self.vars[key] = ctk.StringVar(value=default)
        lbl = ctk.CTkLabel(parent, text=label)
        lbl.grid(row=row, column=col_base, sticky="w", padx=10, pady=6)
        self.input_labels[key] = lbl
        self.base_label_texts[key] = label

        if choices is None:
            wdg: ctk.CTkBaseClass = ctk.CTkEntry(parent, textvariable=self.vars[key])
        else:
            wdg = ctk.CTkOptionMenu(parent, variable=self.vars[key], values=list(choices))
        wdg.grid(row=row, column=col_base + 1, sticky="ew", padx=6, pady=6)
        self.widgets[key] = wdg

        u = ctk.CTkLabel(parent, text=unit, text_color=self.palette.muted_fg)
        u.grid(row=row, column=col_base + 2, sticky="w", padx=6, pady=6)
        self.unit_labels[key] = u

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Flessione", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2)
        )
        ctk.CTkLabel(
            header,
            text=(
                "Sezione + vincoli + carichi puntuali/distribuiti. "
                "Diagrammi V/M/freccia a destra."
            ),
            text_color=self.palette.muted_fg,
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        paned = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=7,
            sashrelief=tk.RAISED,
            bd=0,
            bg=self.palette.border,
        )
        paned.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        left_host = ctk.CTkFrame(paned)
        right = ctk.CTkFrame(paned)
        paned.add(left_host, minsize=520)
        paned.add(right, minsize=420)
        self._paned = paned
        self.after(120, self._apply_default_split_60_40)

        left_scroll = ctk.CTkScrollableFrame(left_host)
        left_scroll.pack(fill="both", expand=True)
        left = left_scroll
        left.grid_columnconfigure(1, weight=1)
        left.grid_columnconfigure(4, weight=1)

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=3)
        right.grid_rowconfigure(3, weight=2)

        row = 0
        ctk.CTkLabel(left, text="Input", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 8)
        )
        row += 1

        self._add_field(
            left,
            "materiale_trave",
            "Materiale trave",
            self.beam_material_names[0] if self.beam_material_names else "",
            row=row,
            col_base=0,
            choices=self.beam_material_names,
        )
        row += 1
        self._add_field(left, "matb_e", "Materiale E", "", "MPa", row=row, col_base=0)
        self._add_field(left, "matb_g", "Materiale G", "", "MPa", row=row, col_base=3)
        row += 1
        self._add_field(left, "matb_sigma_amm", "Materiale sigma amm", "", "MPa", row=row, col_base=0)
        self._add_field(left, "matb_tau_amm", "Materiale tau amm", "", "MPa", row=row, col_base=3)
        row += 1

        self._add_field(
            left,
            "sezione_tipo",
            "Tipo sezione",
            BEAM_SECTION_TYPES[0],
            row=row,
            col_base=0,
            choices=BEAM_SECTION_TYPES,
        )
        self._add_field(
            left,
            "sezione_std",
            "Sezione standard",
            self.beam_section_names[0],
            row=row,
            col_base=3,
            choices=self.beam_section_names,
        )
        row += 1

        self._add_field(left, "sec_d", "Diametro d", "40", "mm", row=row, col_base=0)
        self._add_field(left, "sec_D", "Diametro esterno D", "60", "mm", row=row, col_base=3)
        row += 1
        self._add_field(left, "sec_t", "Spessore t/s", "4", "mm", row=row, col_base=0)
        self._add_field(left, "sec_b", "Base b", "80", "mm", row=row, col_base=3)
        row += 1
        self._add_field(left, "sec_h", "Altezza h", "120", "mm", row=row, col_base=0)
        self._add_field(left, "sec_s", "Spessore s", "4", "mm", row=row, col_base=3)
        row += 1
        ctk.CTkLabel(left, textvariable=self.var_std_section_info, text_color=self.palette.muted_fg).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 6)
        )
        row += 1

        self._add_field(left, "L", "Lunghezza trave L", "1000", "mm", row=row, col_base=0)
        row += 1
        self._add_field(
            left,
            "vincolo_sx",
            "Vincolo sx",
            BEAM_SUPPORT_CHOICES[0],
            row=row,
            col_base=0,
            choices=BEAM_SUPPORT_CHOICES,
        )
        self._add_field(
            left,
            "vincolo_dx",
            "Vincolo dx",
            BEAM_SUPPORT_CHOICES[0],
            row=row,
            col_base=3,
            choices=BEAM_SUPPORT_CHOICES,
        )
        row += 1

        ctk.CTkLabel(left, text="Carichi Puntuali", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(12, 6)
        )
        row += 1

        loads_tree_style = self._configure_load_tables_style()

        add_frame = ctk.CTkFrame(left, fg_color="transparent")
        add_frame.grid(row=row, column=0, columnspan=6, sticky="ew", padx=10, pady=(0, 6))
        add_frame.grid_columnconfigure(1, weight=1)
        add_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(add_frame, text="P").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(add_frame, textvariable=self.var_new_p, width=120).grid(row=0, column=1, sticky="ew", padx=(6, 10))
        ctk.CTkLabel(add_frame, text="x").grid(row=0, column=2, sticky="w")
        ctk.CTkEntry(add_frame, textvariable=self.var_new_x, width=120).grid(row=0, column=3, sticky="ew", padx=(6, 10))
        ctk.CTkButton(add_frame, text="Aggiungi", width=100, command=self._on_add_point_load).grid(row=0, column=4, sticky="e")
        row += 1

        table_host = ctk.CTkFrame(left)
        table_host.grid(row=row, column=0, columnspan=6, sticky="nsew", padx=10, pady=(0, 6))
        table_host.grid_columnconfigure(0, weight=1)
        table_host.grid_rowconfigure(0, weight=1)
        self.tree_point = ttk.Treeview(
            table_host,
            columns=("p", "x"),
            show="headings",
            height=6,
            style=loads_tree_style,
        )
        self.tree_point.heading("p", text="P [N]")
        self.tree_point.heading("x", text="x [mm]")
        self.tree_point.column("p", anchor="e", width=120)
        self.tree_point.column("x", anchor="e", width=120)
        self.tree_point.grid(row=0, column=0, sticky="nsew")
        scr = ttk.Scrollbar(table_host, orient="vertical", command=self.tree_point.yview)
        scr.grid(row=0, column=1, sticky="ns")
        self.tree_point.configure(yscrollcommand=scr.set)
        row += 1

        table_btns = ctk.CTkFrame(left, fg_color="transparent")
        table_btns.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(table_btns, text="Rimuovi selezionato", width=170, command=self._on_remove_point_load).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(table_btns, text="Svuota tabella", width=140, command=self._on_clear_point_loads).pack(side="left")
        row += 1

        ctk.CTkLabel(left, text="Carichi Distribuiti Zonali", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(8, 6)
        )
        row += 1

        add_dist_frame = ctk.CTkFrame(left, fg_color="transparent")
        add_dist_frame.grid(row=row, column=0, columnspan=6, sticky="ew", padx=10, pady=(0, 6))
        add_dist_frame.grid_columnconfigure(1, weight=1)
        add_dist_frame.grid_columnconfigure(3, weight=1)
        add_dist_frame.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(add_dist_frame, text="N totale").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(add_dist_frame, textvariable=self.var_new_qn, width=110).grid(
            row=0, column=1, sticky="ew", padx=(6, 10)
        )
        ctk.CTkLabel(add_dist_frame, text="x inizio").grid(row=0, column=2, sticky="w")
        ctk.CTkEntry(add_dist_frame, textvariable=self.var_new_qx1, width=110).grid(
            row=0, column=3, sticky="ew", padx=(6, 10)
        )
        ctk.CTkLabel(add_dist_frame, text="x fine").grid(row=0, column=4, sticky="w")
        ctk.CTkEntry(add_dist_frame, textvariable=self.var_new_qx2, width=110).grid(
            row=0, column=5, sticky="ew", padx=(6, 10)
        )
        ctk.CTkButton(add_dist_frame, text="Aggiungi", width=100, command=self._on_add_distributed_load).grid(
            row=0, column=6, sticky="e"
        )
        row += 1

        table_dist_host = ctk.CTkFrame(left)
        table_dist_host.grid(row=row, column=0, columnspan=6, sticky="nsew", padx=10, pady=(0, 6))
        table_dist_host.grid_columnconfigure(0, weight=1)
        table_dist_host.grid_rowconfigure(0, weight=1)
        self.tree_dist = ttk.Treeview(
            table_dist_host,
            columns=("n_tot", "x1", "x2"),
            show="headings",
            height=6,
            style=loads_tree_style,
        )
        self.tree_dist.heading("n_tot", text="N totale [N]")
        self.tree_dist.heading("x1", text="x inizio [mm]")
        self.tree_dist.heading("x2", text="x fine [mm]")
        self.tree_dist.column("n_tot", anchor="e", width=130)
        self.tree_dist.column("x1", anchor="e", width=120)
        self.tree_dist.column("x2", anchor="e", width=120)
        self.tree_dist.grid(row=0, column=0, sticky="nsew")
        scr_d = ttk.Scrollbar(table_dist_host, orient="vertical", command=self.tree_dist.yview)
        scr_d.grid(row=0, column=1, sticky="ns")
        self.tree_dist.configure(yscrollcommand=scr_d.set)
        row += 1

        table_dist_btns = ctk.CTkFrame(left, fg_color="transparent")
        table_dist_btns.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(
            table_dist_btns,
            text="Rimuovi selezionato",
            width=170,
            command=self._on_remove_distributed_load,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            table_dist_btns,
            text="Svuota tabella",
            width=140,
            command=self._on_clear_distributed_loads,
        ).pack(side="left")
        row += 1

        cmd = ctk.CTkFrame(left, fg_color="transparent")
        cmd.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(2, 10))
        ctk.CTkButton(cmd, text="CALCOLA", width=120, command=self._on_calculate).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cmd, text="RESET", width=100, command=self._on_reset).pack(side="left")

        ctk.CTkLabel(right, text="Diagrammi", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )
        self.canvas = tk.Canvas(right, bg=self.palette.bg, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _e: self._draw_diagrams())

        ctk.CTkLabel(right, text="Risultati", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=10, pady=(2, 6)
        )
        self.txt_results = ctk.CTkTextbox(right, wrap="word")
        self.txt_results.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.txt_results.configure(state="disabled")

        self.lbl_status = ctk.CTkLabel(right, textvariable=self.var_status, text_color=self.palette.muted_fg)
        self.lbl_status.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))

        mat_var = self.vars.get("materiale_trave")
        if mat_var is not None:
            mat_var.trace_add("write", self._on_material_change)
            self.after(0, self._load_beam_material_data_from_selection)
        sec_var = self.vars.get("sezione_tipo")
        if sec_var is not None:
            sec_var.trace_add("write", self._on_section_type_change)
            self.after(0, self._apply_section_inputs_state)
        sec_std_var = self.vars.get("sezione_std")
        if sec_std_var is not None:
            sec_std_var.trace_add("write", self._on_section_std_change)
            self.after(0, self._load_std_section_dimensions)

    def _apply_default_split_60_40(self) -> None:
        paned = getattr(self, "_paned", None)
        if paned is None:
            return
        try:
            paned.update_idletasks()
            total_w = int(paned.winfo_width())
            if total_w <= 1:
                self.after(120, self._apply_default_split_60_40)
                return
            paned.sash_place(0, int(total_w * 0.60), 0)
        except Exception:
            pass

    def _get_reference_entry_colors(self):
        for ref_key, ref_widget in self.widgets.items():
            if not isinstance(ref_widget, ctk.CTkEntry):
                continue
            if ref_key in ("sec_d", "sec_D", "sec_t", "sec_b", "sec_h", "sec_s"):
                continue
            try:
                return (
                    ref_widget.cget("fg_color"),
                    ref_widget.cget("border_color"),
                    ref_widget.cget("text_color"),
                )
            except Exception:
                break
        return self.palette.entry_bg, self.palette.border, self.palette.entry_fg

    def _set_input_state(self, key: str, enabled: bool) -> None:
        w = self.widgets.get(key)
        if w is None:
            return
        lbl = self.input_labels.get(key)
        unit_lbl = self.unit_labels.get(key)
        base = self.base_label_texts.get(key, key)
        active_fg, active_border, active_text = self._get_reference_entry_colors()
        if lbl is not None:
            lbl.configure(text=base if enabled else f"{base} [DISATTIVO]", text_color=self.palette.fg)
        if unit_lbl is not None:
            unit_lbl.configure(text_color=self.palette.muted_fg)
        if isinstance(w, ctk.CTkOptionMenu):
            try:
                w.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass
            return
        if isinstance(w, ctk.CTkEntry):
            try:
                if enabled:
                    w.configure(
                        state="normal",
                        fg_color=active_fg,
                        border_color=active_border,
                        text_color=active_text,
                    )
                else:
                    w.configure(
                        state="disabled",
                        fg_color=self.palette.disabled_entry_bg,
                        border_color=active_border,
                        text_color=active_text,
                    )
            except Exception:
                pass

    def _apply_section_inputs_state(self) -> None:
        sec_type = (self.vars.get("sezione_tipo").get() or "").strip() if self.vars.get("sezione_tipo") else ""
        for key in ("sec_d", "sec_D", "sec_t", "sec_b", "sec_h", "sec_s", "sezione_std"):
            self._set_input_state(key, enabled=False)
        if sec_type == BEAM_SECTION_ROUND:
            self._set_input_state("sec_d", enabled=True)
        elif sec_type == BEAM_SECTION_TUBE:
            self._set_input_state("sec_D", enabled=True)
            self._set_input_state("sec_t", enabled=True)
        elif sec_type == BEAM_SECTION_RECT:
            self._set_input_state("sec_b", enabled=True)
            self._set_input_state("sec_h", enabled=True)
        elif sec_type == BEAM_SECTION_RECT_TUBE:
            self._set_input_state("sec_b", enabled=True)
            self._set_input_state("sec_h", enabled=True)
            self._set_input_state("sec_s", enabled=True)
        elif sec_type == BEAM_SECTION_STD:
            self._set_input_state("sezione_std", enabled=True)

    def _on_section_type_change(self, *_args) -> None:
        self._apply_section_inputs_state()
        self._load_std_section_dimensions()

    def _on_section_std_change(self, *_args) -> None:
        self._load_std_section_dimensions()

    def _load_std_section_dimensions(self) -> None:
        sec_type = (self.vars.get("sezione_tipo").get() or "").strip() if self.vars.get("sezione_tipo") else ""
        if sec_type != BEAM_SECTION_STD:
            self.var_std_section_info.set("")
            return
        sec_name = (self.vars.get("sezione_std").get() or "").strip() if self.vars.get("sezione_std") else ""
        if not sec_name or sec_name == "-":
            self.var_std_section_info.set("Seleziona un profilo standard.")
            return
        try:
            sec = _beam_section_std(sec_name)
        except Exception:
            self.var_std_section_info.set("Profilo standard non trovato.")
            return
        # Riempi campi geometrici correlati per riferimento visuale.
        self.vars["sec_h"].set(_fmt_number(sec.h_mm, digits=3))
        self.vars["sec_b"].set(_fmt_number(sec.b_mm, digits=3))
        self.vars["sec_s"].set(_fmt_number(sec.tw_mm, digits=3))
        self.vars["sec_t"].set(_fmt_number(sec.tf_mm, digits=3))
        self.var_std_section_info.set(
            f"Profilo {sec.name}: h={_fmt_number(sec.h_mm)} mm, b={_fmt_number(sec.b_mm)} mm, "
            f"tw={_fmt_number(sec.tw_mm)} mm, tf={_fmt_number(sec.tf_mm)} mm, "
            f"Ix={_fmt_number(sec.ix_mm4)} mm^4, Wx={_fmt_number(sec.wx_mm3)} mm^3"
        )

    def _load_beam_material_data_from_selection(self) -> None:
        materiale = (self.vars.get("materiale_trave").get() or "").strip() if self.vars.get("materiale_trave") else ""
        if not materiale:
            return
        try:
            mat = _beam_material(materiale)
        except Exception:
            return
        self.vars["matb_e"].set(_fmt_number(mat.e_mpa, digits=3))
        self.vars["matb_g"].set(_fmt_number(mat.g_mpa, digits=3))
        self.vars["matb_sigma_amm"].set(_fmt_number(mat.sigma_amm_mpa, digits=3))
        self.vars["matb_tau_amm"].set(_fmt_number(mat.tau_amm_mpa, digits=3))

    def _on_material_change(self, *_args) -> None:
        self._load_beam_material_data_from_selection()

    def _on_add_point_load(self) -> None:
        try:
            p = _as_float(self.var_new_p.get(), "Carico puntuale P")
            x = _as_float(self.var_new_x.get(), "Posizione x")
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)
            return
        iid = self.tree_point.insert("", "end", values=(_fmt_number(p, 4), _fmt_number(x, 4)))
        self.tree_point.selection_set(iid)
        self.var_status.set("Carico puntuale aggiunto.")
        self.lbl_status.configure(text_color=self.palette.ok)

    def _on_remove_point_load(self) -> None:
        sel = self.tree_point.selection()
        for iid in sel:
            self.tree_point.delete(iid)

    def _on_clear_point_loads(self) -> None:
        for iid in self.tree_point.get_children():
            self.tree_point.delete(iid)

    def _get_point_loads(self) -> list[tuple[float, float]]:
        loads: list[tuple[float, float]] = []
        for iid in self.tree_point.get_children():
            vals = self.tree_point.item(iid, "values")
            if len(vals) < 2:
                continue
            p = _as_float(str(vals[0]), "Carico puntuale P")
            x = _as_float(str(vals[1]), "Posizione x")
            loads.append((p, x))
        return loads

    def _on_add_distributed_load(self) -> None:
        try:
            n_tot = _as_float(self.var_new_qn.get(), "Distribuito zonale N totale")
            x1 = _as_float(self.var_new_qx1.get(), "Distribuito zonale x inizio")
            x2 = _as_float(self.var_new_qx2.get(), "Distribuito zonale x fine")
            if x2 <= x1:
                raise ValueError("Distribuito zonale: x fine deve essere > x inizio.")
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)
            return
        iid = self.tree_dist.insert(
            "",
            "end",
            values=(_fmt_number(n_tot, 4), _fmt_number(x1, 4), _fmt_number(x2, 4)),
        )
        self.tree_dist.selection_set(iid)
        self.var_status.set("Carico distribuito zonale aggiunto.")
        self.lbl_status.configure(text_color=self.palette.ok)

    def _on_remove_distributed_load(self) -> None:
        sel = self.tree_dist.selection()
        for iid in sel:
            self.tree_dist.delete(iid)

    def _on_clear_distributed_loads(self) -> None:
        for iid in self.tree_dist.get_children():
            self.tree_dist.delete(iid)

    def _get_distributed_loads(self) -> list[tuple[float, float, float]]:
        loads: list[tuple[float, float, float]] = []
        for iid in self.tree_dist.get_children():
            vals = self.tree_dist.item(iid, "values")
            if len(vals) < 3:
                continue
            n_tot = _as_float(str(vals[0]), "Distribuito zonale N totale")
            x1 = _as_float(str(vals[1]), "Distribuito zonale x inizio")
            x2 = _as_float(str(vals[2]), "Distribuito zonale x fine")
            loads.append((n_tot, x1, x2))
        return loads

    def _parse_values(self) -> dict[str, CalcValue]:
        required_float_keys = (
            "matb_e",
            "matb_g",
            "matb_sigma_amm",
            "matb_tau_amm",
            "L",
            "sec_d",
            "sec_D",
            "sec_t",
            "sec_b",
            "sec_h",
            "sec_s",
        )
        out: dict[str, CalcValue] = {}
        for key in ("materiale_trave", "sezione_tipo", "sezione_std", "vincolo_sx", "vincolo_dx"):
            out[key] = (self.vars.get(key).get() or "").strip() if self.vars.get(key) else ""
        for key in required_float_keys:
            raw = (self.vars.get(key).get() or "").strip() if self.vars.get(key) else "0"
            out[key] = _as_float(raw, self.base_label_texts.get(key, key))
        # Campo rimosso dalla UI: manteniamo compatibilita col motore.
        out["q_total"] = 0.0
        return out

    def _show_results(self, rows: CalcRows) -> None:
        _render_results_colored(self.txt_results, rows, self.palette)

    def _draw_diagrams(self) -> None:
        self.canvas.delete("all")
        data = self.diagram_data
        w = int(self.canvas.winfo_width())
        h = int(self.canvas.winfo_height())
        if w < 100 or h < 100:
            return
        if not data:
            self.canvas.create_text(w // 2, h // 2, text="Nessun diagramma disponibile.", fill=self.palette.muted_fg)
            return
        x_vals = data.get("x", [])
        if len(x_vals) < 2:
            self.canvas.create_text(w // 2, h // 2, text="Dati diagrammi insufficienti.", fill=self.palette.muted_fg)
            return

        margin_l, margin_r, margin_t, margin_b = 58, 18, 12, 12
        plot_w = max(10, w - margin_l - margin_r)
        band_h = max(40, (h - margin_t - margin_b) / 3.0)
        x_max = x_vals[-1] if x_vals[-1] > 0 else 1.0

        defs = (
            ("V", "Taglio V [N]", "#e07a5f"),
            ("M", "Momento M [Nmm]", "#3d405b"),
            ("y", "Freccia y [mm]", "#81b29a"),
        )
        for idx, (key, title, color) in enumerate(defs):
            vals = data.get(key, [])
            if len(vals) != len(x_vals):
                continue
            y_top = margin_t + (idx * band_h)
            y_ctr = y_top + (band_h / 2.0)
            self.canvas.create_rectangle(margin_l, y_top, margin_l + plot_w, y_top + band_h, outline=self.palette.border)
            self.canvas.create_line(margin_l, y_ctr, margin_l + plot_w, y_ctr, fill=self.palette.border)
            self.canvas.create_text(8, y_top + 10, text=title, anchor="w", fill=self.palette.fg)

            amp = max((abs(v) for v in vals), default=0.0)
            amp = amp if amp > 1e-12 else 1.0
            self.canvas.create_text(
                margin_l + plot_w - 4,
                y_top + 10,
                text=f"max={_fmt_number(max((abs(v) for v in vals), default=0.0), 3)}",
                anchor="e",
                fill=self.palette.muted_fg,
            )

            points: list[float] = []
            for x, val in zip(x_vals, vals):
                px = margin_l + (x / x_max) * plot_w
                py = y_ctr - (val / amp) * (band_h * 0.42)
                points.extend((px, py))
            self.canvas.create_line(points, fill=color, width=2.0, smooth=False)

        self.canvas.create_text(margin_l, h - 4, text="0", anchor="sw", fill=self.palette.muted_fg)
        self.canvas.create_text(margin_l + plot_w, h - 4, text=f"L={_fmt_number(x_max, 3)} mm", anchor="se", fill=self.palette.muted_fg)

    def _on_calculate(self) -> None:
        try:
            values = self._parse_values()
            point_loads = self._get_point_loads()
            distributed_loads = self._get_distributed_loads()
            rows, diagrams = calc_beam_bending_advanced(values, point_loads, distributed_loads)
            self._show_results(rows)
            self.diagram_data = diagrams
            self._draw_diagrams()
            self.var_status.set("Calcolo completato.")
            self.lbl_status.configure(text_color=self.palette.ok)
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)

    def _on_reset(self) -> None:
        for key, default in self.defaults.items():
            self.vars[key].set(default)
        self.var_new_p.set("1000")
        self.var_new_x.set("500")
        self.var_new_qn.set("2000")
        self.var_new_qx1.set("200")
        self.var_new_qx2.set("800")
        self._on_clear_point_loads()
        self._on_clear_distributed_loads()
        self._load_beam_material_data_from_selection()
        self._apply_section_inputs_state()
        self._load_std_section_dimensions()
        self.diagram_data = None
        self._draw_diagrams()
        self.txt_results.configure(state="normal")
        self.txt_results.delete("1.0", "end")
        self.txt_results.configure(state="disabled")
        self.var_status.set("Inserisci dati trave, carichi e premi CALCOLA.")
        self.lbl_status.configure(text_color=self.palette.muted_fg)


class BeamTorsionPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        palette: Palette,
        beam_material_names: Sequence[str],
    ) -> None:
        super().__init__(master)
        self.palette = palette
        self.beam_material_names = tuple(beam_material_names)

        self.vars: dict[str, ctk.StringVar] = {}
        self.widgets: dict[str, ctk.CTkBaseClass] = {}
        self.input_labels: dict[str, ctk.CTkLabel] = {}
        self.unit_labels: dict[str, ctk.CTkLabel] = {}
        self.base_label_texts: dict[str, str] = {}
        self.defaults: dict[str, str] = {}
        self.diagram_data: dict[str, list[float]] | None = None
        self.var_status = ctk.StringVar(value="Inserisci dati torsione, momenti e premi CALCOLA.")
        self.var_new_m = ctk.StringVar(value="60")
        self.var_new_x = ctk.StringVar(value="500")
        self.var_new_mn = ctk.StringVar(value="30")
        self.var_new_mx1 = ctk.StringVar(value="200")
        self.var_new_mx2 = ctk.StringVar(value="800")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def _add_field(
        self,
        parent,
        key: str,
        label: str,
        default: str = "",
        unit: str = "",
        row: int = 0,
        col_base: int = 0,
        choices: Sequence[str] | None = None,
    ) -> None:
        self.defaults[key] = default
        self.vars[key] = ctk.StringVar(value=default)
        lbl = ctk.CTkLabel(parent, text=label)
        lbl.grid(row=row, column=col_base, sticky="w", padx=10, pady=6)
        self.input_labels[key] = lbl
        self.base_label_texts[key] = label

        if choices is None:
            wdg: ctk.CTkBaseClass = ctk.CTkEntry(parent, textvariable=self.vars[key])
        else:
            wdg = ctk.CTkOptionMenu(parent, variable=self.vars[key], values=list(choices))
        wdg.grid(row=row, column=col_base + 1, sticky="ew", padx=6, pady=6)
        self.widgets[key] = wdg

        u = ctk.CTkLabel(parent, text=unit, text_color=self.palette.muted_fg)
        u.grid(row=row, column=col_base + 2, sticky="w", padx=6, pady=6)
        self.unit_labels[key] = u

    def _configure_load_tables_style(self) -> str:
        style_name = "BeamLoads.Treeview"
        style = ttk.Style(self)
        base = tkfont.nametofont("TkDefaultFont")
        family = str(base.cget("family"))
        base_size = abs(int(base.cget("size")))
        txt_size = max(12, base_size + 2)
        style.configure(style_name, font=(family, txt_size), rowheight=max(28, txt_size + 14))
        style.configure(f"{style_name}.Heading", font=(family, txt_size, "bold"))
        return style_name

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Torsione", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2)
        )
        ctk.CTkLabel(
            header,
            text=(
                "Vincoli con almeno un incastro + momenti torcenti puntuali/distribuiti. "
                "Diagrammi T/theta a destra."
            ),
            text_color=self.palette.muted_fg,
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        paned = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=7,
            sashrelief=tk.RAISED,
            bd=0,
            bg=self.palette.border,
        )
        paned.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        left_host = ctk.CTkFrame(paned)
        right = ctk.CTkFrame(paned)
        paned.add(left_host, minsize=520)
        paned.add(right, minsize=420)
        self._paned = paned
        self.after(120, self._apply_default_split_60_40)

        left_scroll = ctk.CTkScrollableFrame(left_host)
        left_scroll.pack(fill="both", expand=True)
        left = left_scroll
        left.grid_columnconfigure(1, weight=1)
        left.grid_columnconfigure(4, weight=1)

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=3)
        right.grid_rowconfigure(3, weight=2)

        row = 0
        ctk.CTkLabel(left, text="Input", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 8)
        )
        row += 1

        self._add_field(
            left,
            "materiale_trave",
            "Materiale trave",
            self.beam_material_names[0] if self.beam_material_names else "",
            row=row,
            col_base=0,
            choices=self.beam_material_names,
        )
        row += 1
        self._add_field(left, "matb_e", "Materiale E", "", "MPa", row=row, col_base=0)
        self._add_field(left, "matb_g", "Materiale G", "", "MPa", row=row, col_base=3)
        row += 1
        self._add_field(left, "matb_sigma_amm", "Materiale sigma amm", "", "MPa", row=row, col_base=0)
        self._add_field(left, "matb_tau_amm", "Materiale tau amm", "", "MPa", row=row, col_base=3)
        row += 1

        self._add_field(left, "L", "Lunghezza trave L", "1000", "mm", row=row, col_base=0)
        row += 1
        self._add_field(
            left,
            "sezione_tipo",
            "Tipo sezione",
            BEAM_SECTION_ROUND,
            row=row,
            col_base=0,
            choices=BEAM_TORSION_SECTION_TYPES,
        )
        row += 1
        self._add_field(left, "sec_d", "Diametro d", "40", "mm", row=row, col_base=0)
        self._add_field(left, "sec_D", "Diametro esterno D", "60", "mm", row=row, col_base=3)
        row += 1
        self._add_field(left, "sec_t", "Spessore t/s", "4", "mm", row=row, col_base=0)
        self._add_field(left, "sec_b", "Base b", "80", "mm", row=row, col_base=3)
        row += 1
        self._add_field(left, "sec_h", "Altezza h", "120", "mm", row=row, col_base=0)
        self._add_field(left, "sec_s", "Spessore s", "4", "mm", row=row, col_base=3)
        row += 1
        self._add_field(
            left,
            "vincolo_sx",
            "Vincolo sx",
            "INCASTRATA",
            row=row,
            col_base=0,
            choices=("INCASTRATA", "LIBERA"),
        )
        self._add_field(
            left,
            "vincolo_dx",
            "Vincolo dx",
            "LIBERA",
            row=row,
            col_base=3,
            choices=("INCASTRATA", "LIBERA"),
        )
        row += 1

        ctk.CTkLabel(left, text="Momenti Torcenti Puntuali", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(12, 6)
        )
        row += 1

        loads_tree_style = self._configure_load_tables_style()

        add_frame = ctk.CTkFrame(left, fg_color="transparent")
        add_frame.grid(row=row, column=0, columnspan=6, sticky="ew", padx=10, pady=(0, 6))
        add_frame.grid_columnconfigure(1, weight=1)
        add_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(add_frame, text="Mt").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(add_frame, textvariable=self.var_new_m, width=120).grid(row=0, column=1, sticky="ew", padx=(6, 10))
        ctk.CTkLabel(add_frame, text="x").grid(row=0, column=2, sticky="w")
        ctk.CTkEntry(add_frame, textvariable=self.var_new_x, width=120).grid(row=0, column=3, sticky="ew", padx=(6, 10))
        ctk.CTkButton(add_frame, text="Aggiungi", width=100, command=self._on_add_point_torque).grid(
            row=0, column=4, sticky="e"
        )
        row += 1

        table_host = ctk.CTkFrame(left)
        table_host.grid(row=row, column=0, columnspan=6, sticky="nsew", padx=10, pady=(0, 6))
        table_host.grid_columnconfigure(0, weight=1)
        table_host.grid_rowconfigure(0, weight=1)
        self.tree_point = ttk.Treeview(
            table_host,
            columns=("m", "x"),
            show="headings",
            height=6,
            style=loads_tree_style,
        )
        self.tree_point.heading("m", text="Mt [Nm]")
        self.tree_point.heading("x", text="x [mm]")
        self.tree_point.column("m", anchor="e", width=140)
        self.tree_point.column("x", anchor="e", width=120)
        self.tree_point.grid(row=0, column=0, sticky="nsew")
        scr = ttk.Scrollbar(table_host, orient="vertical", command=self.tree_point.yview)
        scr.grid(row=0, column=1, sticky="ns")
        self.tree_point.configure(yscrollcommand=scr.set)
        row += 1

        table_btns = ctk.CTkFrame(left, fg_color="transparent")
        table_btns.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(table_btns, text="Rimuovi selezionato", width=170, command=self._on_remove_point_torque).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(table_btns, text="Svuota tabella", width=140, command=self._on_clear_point_torques).pack(
            side="left"
        )
        row += 1

        ctk.CTkLabel(left, text="Momenti Torcenti Distribuiti Zonali", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(8, 6)
        )
        row += 1

        add_dist_frame = ctk.CTkFrame(left, fg_color="transparent")
        add_dist_frame.grid(row=row, column=0, columnspan=6, sticky="ew", padx=10, pady=(0, 6))
        add_dist_frame.grid_columnconfigure(1, weight=1)
        add_dist_frame.grid_columnconfigure(3, weight=1)
        add_dist_frame.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(add_dist_frame, text="Mt totale").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(add_dist_frame, textvariable=self.var_new_mn, width=110).grid(
            row=0, column=1, sticky="ew", padx=(6, 10)
        )
        ctk.CTkLabel(add_dist_frame, text="x inizio").grid(row=0, column=2, sticky="w")
        ctk.CTkEntry(add_dist_frame, textvariable=self.var_new_mx1, width=110).grid(
            row=0, column=3, sticky="ew", padx=(6, 10)
        )
        ctk.CTkLabel(add_dist_frame, text="x fine").grid(row=0, column=4, sticky="w")
        ctk.CTkEntry(add_dist_frame, textvariable=self.var_new_mx2, width=110).grid(
            row=0, column=5, sticky="ew", padx=(6, 10)
        )
        ctk.CTkButton(add_dist_frame, text="Aggiungi", width=100, command=self._on_add_distributed_torque).grid(
            row=0, column=6, sticky="e"
        )
        row += 1

        table_dist_host = ctk.CTkFrame(left)
        table_dist_host.grid(row=row, column=0, columnspan=6, sticky="nsew", padx=10, pady=(0, 6))
        table_dist_host.grid_columnconfigure(0, weight=1)
        table_dist_host.grid_rowconfigure(0, weight=1)
        self.tree_dist = ttk.Treeview(
            table_dist_host,
            columns=("m_tot", "x1", "x2"),
            show="headings",
            height=6,
            style=loads_tree_style,
        )
        self.tree_dist.heading("m_tot", text="Mt totale [Nm]")
        self.tree_dist.heading("x1", text="x inizio [mm]")
        self.tree_dist.heading("x2", text="x fine [mm]")
        self.tree_dist.column("m_tot", anchor="e", width=150)
        self.tree_dist.column("x1", anchor="e", width=120)
        self.tree_dist.column("x2", anchor="e", width=120)
        self.tree_dist.grid(row=0, column=0, sticky="nsew")
        scr_d = ttk.Scrollbar(table_dist_host, orient="vertical", command=self.tree_dist.yview)
        scr_d.grid(row=0, column=1, sticky="ns")
        self.tree_dist.configure(yscrollcommand=scr_d.set)
        row += 1

        table_dist_btns = ctk.CTkFrame(left, fg_color="transparent")
        table_dist_btns.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(
            table_dist_btns,
            text="Rimuovi selezionato",
            width=170,
            command=self._on_remove_distributed_torque,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            table_dist_btns,
            text="Svuota tabella",
            width=140,
            command=self._on_clear_distributed_torques,
        ).pack(side="left")
        row += 1

        cmd = ctk.CTkFrame(left, fg_color="transparent")
        cmd.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(2, 10))
        ctk.CTkButton(cmd, text="CALCOLA", width=120, command=self._on_calculate).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cmd, text="RESET", width=100, command=self._on_reset).pack(side="left")

        ctk.CTkLabel(right, text="Diagrammi", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )
        self.canvas = tk.Canvas(right, bg=self.palette.bg, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _e: self._draw_diagrams())

        ctk.CTkLabel(right, text="Risultati", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=10, pady=(2, 6)
        )
        self.txt_results = ctk.CTkTextbox(right, wrap="word")
        self.txt_results.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.txt_results.configure(state="disabled")

        self.lbl_status = ctk.CTkLabel(right, textvariable=self.var_status, text_color=self.palette.muted_fg)
        self.lbl_status.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))

        mat_var = self.vars.get("materiale_trave")
        if mat_var is not None:
            mat_var.trace_add("write", self._on_material_change)
            self.after(0, self._load_beam_material_data_from_selection)
        sec_var = self.vars.get("sezione_tipo")
        if sec_var is not None:
            sec_var.trace_add("write", self._on_section_type_change)
            self.after(0, self._apply_section_inputs_state)

    def _apply_default_split_60_40(self) -> None:
        paned = getattr(self, "_paned", None)
        if paned is None:
            return
        try:
            paned.update_idletasks()
            total_w = int(paned.winfo_width())
            if total_w <= 1:
                self.after(120, self._apply_default_split_60_40)
                return
            paned.sash_place(0, int(total_w * 0.60), 0)
        except Exception:
            pass

    def _get_reference_entry_colors(self):
        for ref_key, ref_widget in self.widgets.items():
            if not isinstance(ref_widget, ctk.CTkEntry):
                continue
            if ref_key in ("sec_d", "sec_D", "sec_t", "sec_b", "sec_h", "sec_s"):
                continue
            try:
                return (
                    ref_widget.cget("fg_color"),
                    ref_widget.cget("border_color"),
                    ref_widget.cget("text_color"),
                )
            except Exception:
                break
        return self.palette.entry_bg, self.palette.border, self.palette.entry_fg

    def _set_input_state(self, key: str, enabled: bool) -> None:
        w = self.widgets.get(key)
        if w is None:
            return
        lbl = self.input_labels.get(key)
        unit_lbl = self.unit_labels.get(key)
        base = self.base_label_texts.get(key, key)
        active_fg, active_border, active_text = self._get_reference_entry_colors()
        if lbl is not None:
            lbl.configure(text=base if enabled else f"{base} [DISATTIVO]", text_color=self.palette.fg)
        if unit_lbl is not None:
            unit_lbl.configure(text_color=self.palette.muted_fg)
        if isinstance(w, ctk.CTkOptionMenu):
            try:
                w.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass
            return
        if isinstance(w, ctk.CTkEntry):
            try:
                if enabled:
                    w.configure(
                        state="normal",
                        fg_color=active_fg,
                        border_color=active_border,
                        text_color=active_text,
                    )
                else:
                    w.configure(
                        state="disabled",
                        fg_color=self.palette.disabled_entry_bg,
                        border_color=active_border,
                        text_color=active_text,
                    )
            except Exception:
                pass

    def _apply_section_inputs_state(self) -> None:
        sec_type = (self.vars.get("sezione_tipo").get() or "").strip() if self.vars.get("sezione_tipo") else ""
        for key in ("sec_d", "sec_D", "sec_t", "sec_b", "sec_h", "sec_s"):
            self._set_input_state(key, enabled=False)
        if sec_type == BEAM_SECTION_ROUND:
            self._set_input_state("sec_d", enabled=True)
        elif sec_type == BEAM_SECTION_TUBE:
            self._set_input_state("sec_D", enabled=True)
            self._set_input_state("sec_t", enabled=True)
        elif sec_type == BEAM_SECTION_RECT:
            self._set_input_state("sec_b", enabled=True)
            self._set_input_state("sec_h", enabled=True)
        elif sec_type == BEAM_SECTION_RECT_TUBE:
            self._set_input_state("sec_b", enabled=True)
            self._set_input_state("sec_h", enabled=True)
            self._set_input_state("sec_s", enabled=True)

    def _on_section_type_change(self, *_args) -> None:
        self._apply_section_inputs_state()

    def _load_beam_material_data_from_selection(self) -> None:
        materiale = (self.vars.get("materiale_trave").get() or "").strip() if self.vars.get("materiale_trave") else ""
        if not materiale:
            return
        try:
            mat = _beam_material(materiale)
        except Exception:
            return
        self.vars["matb_e"].set(_fmt_number(mat.e_mpa, digits=3))
        self.vars["matb_g"].set(_fmt_number(mat.g_mpa, digits=3))
        self.vars["matb_sigma_amm"].set(_fmt_number(mat.sigma_amm_mpa, digits=3))
        self.vars["matb_tau_amm"].set(_fmt_number(mat.tau_amm_mpa, digits=3))

    def _on_material_change(self, *_args) -> None:
        self._load_beam_material_data_from_selection()

    def _on_add_point_torque(self) -> None:
        try:
            m = _as_float(self.var_new_m.get(), "Momento torcente puntuale Mt")
            x = _as_float(self.var_new_x.get(), "Posizione x")
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)
            return
        iid = self.tree_point.insert("", "end", values=(_fmt_number(m, 4), _fmt_number(x, 4)))
        self.tree_point.selection_set(iid)
        self.var_status.set("Momento torcente puntuale aggiunto.")
        self.lbl_status.configure(text_color=self.palette.ok)

    def _on_remove_point_torque(self) -> None:
        sel = self.tree_point.selection()
        for iid in sel:
            self.tree_point.delete(iid)

    def _on_clear_point_torques(self) -> None:
        for iid in self.tree_point.get_children():
            self.tree_point.delete(iid)

    def _get_point_torques(self) -> list[tuple[float, float]]:
        loads: list[tuple[float, float]] = []
        for iid in self.tree_point.get_children():
            vals = self.tree_point.item(iid, "values")
            if len(vals) < 2:
                continue
            m = _as_float(str(vals[0]), "Momento torcente puntuale Mt")
            x = _as_float(str(vals[1]), "Posizione x")
            loads.append((m, x))
        return loads

    def _on_add_distributed_torque(self) -> None:
        try:
            m_tot = _as_float(self.var_new_mn.get(), "Distribuito torsione Mt totale")
            x1 = _as_float(self.var_new_mx1.get(), "Distribuito torsione x inizio")
            x2 = _as_float(self.var_new_mx2.get(), "Distribuito torsione x fine")
            if x2 <= x1:
                raise ValueError("Distribuito torsione: x fine deve essere > x inizio.")
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)
            return
        iid = self.tree_dist.insert(
            "",
            "end",
            values=(_fmt_number(m_tot, 4), _fmt_number(x1, 4), _fmt_number(x2, 4)),
        )
        self.tree_dist.selection_set(iid)
        self.var_status.set("Momento torcente distribuito zonale aggiunto.")
        self.lbl_status.configure(text_color=self.palette.ok)

    def _on_remove_distributed_torque(self) -> None:
        sel = self.tree_dist.selection()
        for iid in sel:
            self.tree_dist.delete(iid)

    def _on_clear_distributed_torques(self) -> None:
        for iid in self.tree_dist.get_children():
            self.tree_dist.delete(iid)

    def _get_distributed_torques(self) -> list[tuple[float, float, float]]:
        loads: list[tuple[float, float, float]] = []
        for iid in self.tree_dist.get_children():
            vals = self.tree_dist.item(iid, "values")
            if len(vals) < 3:
                continue
            m_tot = _as_float(str(vals[0]), "Distribuito torsione Mt totale")
            x1 = _as_float(str(vals[1]), "Distribuito torsione x inizio")
            x2 = _as_float(str(vals[2]), "Distribuito torsione x fine")
            loads.append((m_tot, x1, x2))
        return loads

    def _parse_values(self) -> dict[str, CalcValue]:
        required_float_keys = (
            "matb_e",
            "matb_g",
            "matb_sigma_amm",
            "matb_tau_amm",
            "L",
            "sec_d",
            "sec_D",
            "sec_t",
            "sec_b",
            "sec_h",
            "sec_s",
        )
        out: dict[str, CalcValue] = {}
        for key in ("materiale_trave", "sezione_tipo", "vincolo_sx", "vincolo_dx"):
            out[key] = (self.vars.get(key).get() or "").strip() if self.vars.get(key) else ""
        for key in required_float_keys:
            raw = (self.vars.get(key).get() or "").strip() if self.vars.get(key) else "0"
            out[key] = _as_float(raw, self.base_label_texts.get(key, key))
        out["mt_total"] = 0.0
        return out

    def _show_results(self, rows: CalcRows) -> None:
        _render_results_colored(self.txt_results, rows, self.palette)

    def _draw_diagrams(self) -> None:
        self.canvas.delete("all")
        data = self.diagram_data
        w = int(self.canvas.winfo_width())
        h = int(self.canvas.winfo_height())
        if w < 100 or h < 100:
            return
        if not data:
            self.canvas.create_text(w // 2, h // 2, text="Nessun diagramma disponibile.", fill=self.palette.muted_fg)
            return
        x_vals = data.get("x", [])
        if len(x_vals) < 2:
            self.canvas.create_text(w // 2, h // 2, text="Dati diagrammi insufficienti.", fill=self.palette.muted_fg)
            return

        margin_l, margin_r, margin_t, margin_b = 58, 18, 12, 12
        plot_w = max(10, w - margin_l - margin_r)
        band_h = max(50, (h - margin_t - margin_b) / 2.0)
        x_max = x_vals[-1] if x_vals[-1] > 0 else 1.0

        defs = (
            ("T", "Momento torcente T [Nm]", "#e07a5f"),
            ("theta_deg", "Angolo torsione theta [gradi]", "#81b29a"),
        )
        for idx, (key, title, color) in enumerate(defs):
            vals = data.get(key, [])
            if len(vals) != len(x_vals):
                continue
            y_top = margin_t + (idx * band_h)
            y_ctr = y_top + (band_h / 2.0)
            self.canvas.create_rectangle(margin_l, y_top, margin_l + plot_w, y_top + band_h, outline=self.palette.border)
            self.canvas.create_line(margin_l, y_ctr, margin_l + plot_w, y_ctr, fill=self.palette.border)
            self.canvas.create_text(8, y_top + 10, text=title, anchor="w", fill=self.palette.fg)

            amp = max((abs(v) for v in vals), default=0.0)
            amp = amp if amp > 1e-12 else 1.0
            self.canvas.create_text(
                margin_l + plot_w - 4,
                y_top + 10,
                text=f"max={_fmt_number(max((abs(v) for v in vals), default=0.0), 3)}",
                anchor="e",
                fill=self.palette.muted_fg,
            )

            points: list[float] = []
            for x, val in zip(x_vals, vals):
                px = margin_l + (x / x_max) * plot_w
                py = y_ctr - (val / amp) * (band_h * 0.42)
                points.extend((px, py))
            self.canvas.create_line(points, fill=color, width=2.0, smooth=False)

        self.canvas.create_text(margin_l, h - 4, text="0", anchor="sw", fill=self.palette.muted_fg)
        self.canvas.create_text(margin_l + plot_w, h - 4, text=f"L={_fmt_number(x_max, 3)} mm", anchor="se", fill=self.palette.muted_fg)

    def _on_calculate(self) -> None:
        try:
            values = self._parse_values()
            point_torques = self._get_point_torques()
            distributed_torques = self._get_distributed_torques()
            rows, diagrams = calc_beam_torsion_advanced(values, point_torques, distributed_torques)
            self._show_results(rows)
            self.diagram_data = diagrams
            self._draw_diagrams()
            self.var_status.set("Calcolo completato.")
            self.lbl_status.configure(text_color=self.palette.ok)
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)

    def _on_reset(self) -> None:
        for key, default in self.defaults.items():
            self.vars[key].set(default)
        self.var_new_m.set("60")
        self.var_new_x.set("500")
        self.var_new_mn.set("30")
        self.var_new_mx1.set("200")
        self.var_new_mx2.set("800")
        self._on_clear_point_torques()
        self._on_clear_distributed_torques()
        self._load_beam_material_data_from_selection()
        self._apply_section_inputs_state()
        self.diagram_data = None
        self._draw_diagrams()
        self.txt_results.configure(state="normal")
        self.txt_results.delete("1.0", "end")
        self.txt_results.configure(state="disabled")
        self.var_status.set("Inserisci dati torsione, momenti e premi CALCOLA.")
        self.lbl_status.configure(text_color=self.palette.muted_fg)


class FitTolerancePanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        palette: Palette,
        material_names: Sequence[str],
        hole_positions: Sequence[str],
        shaft_positions: Sequence[str],
        iso_grades: Sequence[str],
    ) -> None:
        super().__init__(master)
        self.palette = palette
        self.material_names = tuple(material_names)
        self.hole_positions = tuple(hole_positions)
        self.shaft_positions = tuple(shaft_positions)
        self.iso_grades = tuple(iso_grades)

        self.vars: dict[str, ctk.StringVar] = {}
        self.widgets: dict[str, ctk.CTkBaseClass] = {}
        self.input_labels: dict[str, ctk.CTkLabel] = {}
        self.unit_labels: dict[str, ctk.CTkLabel] = {}
        self.base_label_texts: dict[str, str] = {}
        self.defaults: dict[str, str] = {}
        self.var_status = ctk.StringVar(value="Inserisci dati e premi CALCOLA.")
        self.diagram_data: dict[str, float] | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def _add_field(
        self,
        parent,
        key: str,
        label: str,
        default: str = "",
        unit: str = "",
        row: int = 0,
        col_base: int = 0,
        choices: Sequence[str] | None = None,
    ) -> None:
        self.defaults[key] = default
        self.vars[key] = ctk.StringVar(value=default)
        lbl = ctk.CTkLabel(parent, text=label)
        lbl.grid(row=row, column=col_base, sticky="w", padx=10, pady=6)
        self.input_labels[key] = lbl
        self.base_label_texts[key] = label

        if choices is None:
            wdg: ctk.CTkBaseClass = ctk.CTkEntry(parent, textvariable=self.vars[key])
        else:
            wdg = ctk.CTkOptionMenu(parent, variable=self.vars[key], values=list(choices))
        wdg.grid(row=row, column=col_base + 1, sticky="ew", padx=6, pady=6)
        self.widgets[key] = wdg

        u = ctk.CTkLabel(parent, text=unit, text_color=self.palette.muted_fg)
        u.grid(row=row, column=col_base + 2, sticky="w", padx=6, pady=6)
        self.unit_labels[key] = u

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Accoppiamento Foro/Albero", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2)
        )
        ctk.CTkLabel(
            header,
            text="Tolleranze ISO foro/albero + materiali + temperatura esercizio (riferimento 20 gradiC).",
            text_color=self.palette.muted_fg,
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        paned = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=7,
            sashrelief=tk.RAISED,
            bd=0,
            bg=self.palette.border,
        )
        paned.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        left_host = ctk.CTkFrame(paned)
        right = ctk.CTkFrame(paned)
        paned.add(left_host, minsize=500)
        paned.add(right, minsize=420)
        self._paned = paned
        self.after(120, self._apply_default_split_60_40)

        left = ctk.CTkScrollableFrame(left_host)
        left.pack(fill="both", expand=True)
        left.grid_columnconfigure(1, weight=1)
        left.grid_columnconfigure(4, weight=1)

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=3)
        right.grid_rowconfigure(3, weight=2)

        row = 0
        ctk.CTkLabel(left, text="Input", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 8)
        )
        row += 1

        self._add_field(left, "d_nom", "Diametro nominale d", "30", "mm", row=row, col_base=0)
        self._add_field(left, "temp_c", "Temperatura esercizio", "20", "gradiC", row=row, col_base=3)
        row += 1

        hole_pos_default = "H" if "H" in self.hole_positions else (self.hole_positions[0] if self.hole_positions else "H")
        shaft_pos_default = "h" if "h" in self.shaft_positions else (self.shaft_positions[0] if self.shaft_positions else "h")
        hole_it_default = "7" if "7" in self.iso_grades else (self.iso_grades[0] if self.iso_grades else "7")
        shaft_it_default = "6" if "6" in self.iso_grades else (self.iso_grades[0] if self.iso_grades else "6")

        self._add_field(
            left,
            "shaft_pos",
            "Albero posizione toll.",
            shaft_pos_default,
            row=row,
            col_base=0,
            choices=self.shaft_positions,
        )
        self._add_field(
            left,
            "hole_pos",
            "Foro posizione toll.",
            hole_pos_default,
            row=row,
            col_base=3,
            choices=self.hole_positions,
        )
        row += 1

        self._add_field(
            left,
            "shaft_it",
            "Albero grado qualita",
            shaft_it_default,
            row=row,
            col_base=0,
            choices=self.iso_grades,
        )
        self._add_field(
            left,
            "hole_it",
            "Foro grado qualita",
            hole_it_default,
            row=row,
            col_base=3,
            choices=self.iso_grades,
        )
        row += 1

        self._add_field(
            left,
            "mat_shaft",
            "Materiale albero",
            self.material_names[0] if self.material_names else "",
            row=row,
            col_base=0,
            choices=self.material_names,
        )
        self._add_field(
            left,
            "mat_hole",
            "Materiale foro",
            self.material_names[0] if self.material_names else "",
            row=row,
            col_base=3,
            choices=self.material_names,
        )
        row += 1

        cmd = ctk.CTkFrame(left, fg_color="transparent")
        cmd.grid(row=row, column=0, columnspan=6, sticky="w", padx=10, pady=(6, 10))
        ctk.CTkButton(cmd, text="CALCOLA", width=120, command=self._on_calculate).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cmd, text="RESET", width=100, command=self._on_reset).pack(side="left")

        ctk.CTkLabel(right, text="Grafico Accoppiamento", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )
        self.canvas = tk.Canvas(right, bg=self.palette.bg, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _e: self._draw_graph())

        ctk.CTkLabel(right, text="Risultati", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=10, pady=(2, 6)
        )
        self.txt_results = ctk.CTkTextbox(right, wrap="word")
        self.txt_results.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.txt_results.configure(state="disabled")

        self.lbl_status = ctk.CTkLabel(right, textvariable=self.var_status, text_color=self.palette.muted_fg)
        self.lbl_status.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))

    def _apply_default_split_60_40(self) -> None:
        paned = getattr(self, "_paned", None)
        if paned is None:
            return
        try:
            paned.update_idletasks()
            total_w = int(paned.winfo_width())
            if total_w <= 1:
                self.after(120, self._apply_default_split_60_40)
                return
            paned.sash_place(0, int(total_w * 0.60), 0)
        except Exception:
            pass

    def _parse_values(self) -> dict[str, CalcValue]:
        hole_pos = (self.vars.get("hole_pos").get() or "").strip() if self.vars.get("hole_pos") else ""
        hole_it = (self.vars.get("hole_it").get() or "").strip() if self.vars.get("hole_it") else ""
        shaft_pos = (self.vars.get("shaft_pos").get() or "").strip() if self.vars.get("shaft_pos") else ""
        shaft_it = (self.vars.get("shaft_it").get() or "").strip() if self.vars.get("shaft_it") else ""
        out: dict[str, CalcValue] = {
            "hole_pos": hole_pos,
            "hole_it": hole_it,
            "shaft_pos": shaft_pos,
            "shaft_it": shaft_it,
            "hole_iso": f"{hole_pos}{hole_it}" if hole_pos and hole_it else "",
            "shaft_iso": f"{shaft_pos}{shaft_it}" if shaft_pos and shaft_it else "",
            "mat_hole": (self.vars.get("mat_hole").get() or "").strip() if self.vars.get("mat_hole") else "",
            "mat_shaft": (self.vars.get("mat_shaft").get() or "").strip() if self.vars.get("mat_shaft") else "",
        }
        out["d_nom"] = _as_float((self.vars.get("d_nom").get() or "").strip(), "Diametro nominale d")
        out["temp_c"] = _as_float((self.vars.get("temp_c").get() or "").strip(), "Temperatura esercizio")
        return out

    def _show_results(self, rows: CalcRows) -> None:
        _render_results_colored(self.txt_results, rows, self.palette)

    def _draw_interval(self, x1: float, x2: float, y: float, color: str, label: str) -> None:
        self.canvas.create_line(x1, y, x2, y, fill=color, width=8, capstyle="round")
        self.canvas.create_text(8, y, text=label, fill=self.palette.fg, anchor="w")
        self.canvas.create_line(x1, y - 8, x1, y + 8, fill=color, width=2)
        self.canvas.create_line(x2, y - 8, x2, y + 8, fill=color, width=2)

    def _draw_graph(self) -> None:
        self.canvas.delete("all")
        data = self.diagram_data
        w = int(self.canvas.winfo_width())
        h = int(self.canvas.winfo_height())
        if w < 120 or h < 120:
            return
        if not data:
            self.canvas.create_text(w // 2, h // 2, text="Nessun grafico disponibile.", fill=self.palette.muted_fg)
            return

        margin_l, margin_r, margin_t, margin_b = 110, 20, 20, 48
        plot_w = max(10, w - margin_l - margin_r)
        plot_h = max(10, h - margin_t - margin_b)

        values = (
            data["hole_min_20"],
            data["hole_max_20"],
            data["shaft_min_20"],
            data["shaft_max_20"],
            data["hole_min_t"],
            data["hole_max_t"],
            data["shaft_min_t"],
            data["shaft_max_t"],
        )
        v_min = min(values)
        v_max = max(values)
        span = max(v_max - v_min, 0.001)
        pad = span * 0.18
        axis_min = v_min - pad
        axis_max = v_max + pad

        def px(v: float) -> float:
            return margin_l + ((v - axis_min) / (axis_max - axis_min)) * plot_w

        y_hole_20 = margin_t + (plot_h * 0.20)
        y_shaft_20 = margin_t + (plot_h * 0.36)
        y_hole_t = margin_t + (plot_h * 0.62)
        y_shaft_t = margin_t + (plot_h * 0.78)

        self._draw_interval(px(data["hole_min_20"]), px(data["hole_max_20"]), y_hole_20, "#4ea8de", "Foro @20C")
        self._draw_interval(px(data["shaft_min_20"]), px(data["shaft_max_20"]), y_shaft_20, "#f4a261", "Albero @20C")
        self._draw_interval(px(data["hole_min_t"]), px(data["hole_max_t"]), y_hole_t, "#2a9d8f", "Foro @T")
        self._draw_interval(px(data["shaft_min_t"]), px(data["shaft_max_t"]), y_shaft_t, "#e76f51", "Albero @T")

        x_nom = px(data["d_nom"])
        self.canvas.create_line(x_nom, margin_t - 2, x_nom, h - margin_b + 6, fill=self.palette.border, dash=(3, 3))
        self.canvas.create_text(x_nom, margin_t - 6, text="d nominale", fill=self.palette.muted_fg, anchor="s")

        y_axis = h - margin_b + 10
        self.canvas.create_line(margin_l, y_axis, margin_l + plot_w, y_axis, fill=self.palette.border)
        self.canvas.create_text(margin_l, y_axis + 14, text=_fmt_number(axis_min, 5), fill=self.palette.muted_fg, anchor="w")
        self.canvas.create_text(
            margin_l + plot_w, y_axis + 14, text=_fmt_number(axis_max, 5), fill=self.palette.muted_fg, anchor="e"
        )
        self.canvas.create_text(
            margin_l + (plot_w / 2.0),
            y_axis + 14,
            text=f"T={_fmt_number(data['temp_c'])} gradiC (rif. 20 gradiC)",
            fill=self.palette.muted_fg,
            anchor="n",
        )

        self.canvas.create_text(
            margin_l,
            h - 6,
            text=(
                f"Delta foro-albero @20C: {_fmt_number(data['j_min_20'], 6)} .. {_fmt_number(data['j_max_20'], 6)} mm   |   "
                f"Delta foro-albero @T: {_fmt_number(data['j_min_t'], 6)} .. {_fmt_number(data['j_max_t'], 6)} mm"
            ),
            fill=self.palette.fg,
            anchor="sw",
        )

    def _on_calculate(self) -> None:
        try:
            values = self._parse_values()
            rows, graph = calc_tolerance_fit_iso_thermal(values)
            self._show_results(rows)
            self.diagram_data = graph
            self._draw_graph()
            self.var_status.set("Calcolo accoppiamento completato.")
            self.lbl_status.configure(text_color=self.palette.ok)
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)

    def _on_reset(self) -> None:
        for key, default in self.defaults.items():
            self.vars[key].set(default)
        self.diagram_data = None
        self._draw_graph()
        self.txt_results.configure(state="normal")
        self.txt_results.delete("1.0", "end")
        self.txt_results.configure(state="disabled")
        self.var_status.set("Inserisci dati e premi CALCOLA.")
        self.lbl_status.configure(text_color=self.palette.muted_fg)


class CalculatorPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        description: str,
        fields: Sequence[FieldSpec],
        calc_fn: CalcFn,
        palette: Palette,
    ):
        super().__init__(master)
        self.title = title
        self.description = description
        self.fields = fields
        self.calc_fn = calc_fn
        self.palette = palette

        self.vars: dict[str, ctk.StringVar] = {}
        self.defaults: dict[str, str] = {}
        self.widgets: dict[str, ctk.CTkBaseClass] = {}
        self.input_labels: dict[str, ctk.CTkLabel] = {}
        self.unit_labels: dict[str, ctk.CTkLabel] = {}
        self.base_label_texts: dict[str, str] = {}
        self.var_status = ctk.StringVar(value="Inserisci dati e premi CALCOLA.")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=self.title, font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2)
        )
        ctk.CTkLabel(header, text=self.description, text_color=self.palette.muted_fg).grid(
            row=1, column=0, sticky="w", padx=10, pady=(0, 10)
        )

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        paned = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=7,
            sashrelief=tk.RAISED,
            bd=0,
            bg=self.palette.border,
        )
        paned.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        left_host = ctk.CTkFrame(paned)
        right = ctk.CTkFrame(paned)

        paned.add(left_host, minsize=460)
        paned.add(right, minsize=380)
        self._paned = paned
        self.after(120, self._apply_default_split_60_40)

        left_scroll = ctk.CTkScrollableFrame(left_host)
        left_scroll.pack(fill="both", expand=True)

        left = left_scroll
        left.grid_columnconfigure(1, weight=1)
        left.grid_columnconfigure(4, weight=1)

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Input", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 8)
        )

        def _add_field(spec: FieldSpec, row: int, col_base: int) -> None:
            default = spec.default
            if spec.field_type in ("choice", "radio") and not default and spec.choices:
                default = spec.choices[0]
            self.defaults[spec.key] = default
            self.vars[spec.key] = ctk.StringVar(value=default)

            lbl = ctk.CTkLabel(left, text=spec.label)
            lbl.grid(row=row, column=col_base, sticky="w", padx=10, pady=6)
            self.input_labels[spec.key] = lbl
            self.base_label_texts[spec.key] = spec.label

            if spec.field_type == "choice":
                widget = ctk.CTkOptionMenu(left, values=list(spec.choices), variable=self.vars[spec.key])
            elif spec.field_type == "radio":
                widget = ctk.CTkFrame(left, fg_color="transparent")
                for option in spec.choices:
                    rb = ctk.CTkRadioButton(widget, text=option, value=option, variable=self.vars[spec.key])
                    rb.pack(anchor="w")
            else:
                widget = ctk.CTkEntry(left, textvariable=self.vars[spec.key])

            widget.grid(row=row, column=col_base + 1, sticky="ew", padx=6, pady=6)
            self.widgets[spec.key] = widget

            unit_lbl = ctk.CTkLabel(left, text=spec.unit, text_color=self.palette.muted_fg)
            unit_lbl.grid(row=row, column=col_base + 2, sticky="w", padx=6, pady=6)
            self.unit_labels[spec.key] = unit_lbl

        row_idx = self._layout_input_fields(left, _add_field)

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.grid(row=row_idx, column=0, columnspan=6, sticky="w", padx=10, pady=(10, 10))
        ctk.CTkButton(btns, text="CALCOLA", width=120, command=self._on_calculate).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="RESET", width=100, command=self._on_reset).pack(side="left")

        ctk.CTkLabel(right, text="Risultati", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 8)
        )
        self.txt_results = ctk.CTkTextbox(right, wrap="word")
        self.txt_results.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.txt_results.configure(state="disabled")

        self.lbl_status = ctk.CTkLabel(right, textvariable=self.var_status, text_color=self.palette.muted_fg)
        self.lbl_status.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

        material_var = self.vars.get("materiale")
        if material_var is not None and self._has_spring_material_data_fields():
            material_var.trace_add("write", self._on_material_change)
            self.after(0, self._load_spring_material_data_from_selection)

        beam_material_var = self.vars.get("materiale_trave")
        if beam_material_var is not None and self._has_beam_material_data_fields():
            beam_material_var.trace_add("write", self._on_beam_material_change)
            self.after(0, self._load_beam_material_data_from_selection)

        disc_source_var = self.vars.get("tazza_source")
        if disc_source_var is not None:
            disc_source_var.trace_add("write", self._on_disc_source_change)
        disc_std_var = self.vars.get("tazza_std")
        if disc_std_var is not None:
            disc_std_var.trace_add("write", self._on_disc_standard_change)
        if disc_source_var is not None or disc_std_var is not None:
            self.after(0, self._on_disc_source_change)

        mode_var = self.vars.get("modo_calcolo")
        if mode_var is not None:
            mode_var.trace_add("write", self._on_mode_change)
            self.after(0, self._apply_mode_inputs_state)
        vm_mode_var = self.vars.get("vm_mode")
        if vm_mode_var is not None:
            vm_mode_var.trace_add("write", self._on_mode_change)
            self.after(0, self._apply_mode_inputs_state)

        vm_thread_family_var = self.vars.get("vm_thread_family")
        vm_thread_var = self.vars.get("vm_thread_std")
        if vm_thread_family_var is not None and vm_thread_var is not None and self._has_screw_thread_family_fields():
            vm_thread_family_var.trace_add("write", self._on_screw_thread_family_change)
            vm_thread_var.trace_add("write", self._on_screw_thread_change)
            self.after(0, self._on_screw_thread_family_change)
        elif vm_thread_var is not None and self._has_screw_thread_fields():
            vm_thread_var.trace_add("write", self._on_screw_thread_change)
            self.after(0, self._load_screw_thread_from_selection)

    def _layout_input_fields(self, left, add_field: Callable[[FieldSpec, int, int], None]) -> int:
        if self.title == SCREW_NUT_PANEL_TITLE:
            return self._layout_power_screw_fields(left, add_field)
        if self.title in GEAR_PANEL_TITLES:
            return self._layout_gear_fields(left, add_field)

        paired_rows = (
            ("mat_e", "mat_g"),
            ("mat_sigma_amm", "mat_tau_amm"),
            ("matb_e", "matb_g"),
            ("matb_sigma_amm", "matb_tau_amm"),
            ("b_fixed", "b_free"),
            ("tazza_source", "tazza_std"),
            ("n_series", "n_parallel"),
            ("f1", "f2"),
            ("F1", "F2"),
        )
        pair_first_to_second = {a: b for a, b in paired_rows}
        pair_second_set = {b for _a, b in paired_rows}
        fields_by_key = {f.key: f for f in self.fields}

        row_idx = 1
        for spec in self.fields:
            if spec.key in pair_second_set:
                continue
            if spec.key in pair_first_to_second:
                add_field(spec, row_idx, 0)
                pair_key = pair_first_to_second[spec.key]
                pair_spec = fields_by_key.get(pair_key)
                if pair_spec is not None:
                    add_field(pair_spec, row_idx, 3)
                row_idx += 1
                continue

            add_field(spec, row_idx, 0)
            row_idx += 1

        return row_idx

    def _layout_power_screw_fields(self, left, add_field: Callable[[FieldSpec, int, int], None]) -> int:
        fields_by_key = {f.key: f for f in self.fields}
        used_keys: set[str] = set()
        row_idx = 1

        ctk.CTkLabel(left, text="Dati comuni", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row_idx, column=0, columnspan=6, sticky="w", padx=10, pady=(8, 2)
        )
        row_idx += 1
        common_keys = ("vm_thread_family", "vm_thread_std", "vm_d", "vm_p", "vm_mu")
        for key in common_keys:
            spec = fields_by_key.get(key)
            if spec is None:
                continue
            add_field(spec, row_idx, 0)
            used_keys.add(key)
            row_idx += 1

        ctk.CTkLabel(left, text="Dati madrevite", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2)
        )
        ctk.CTkLabel(left, text="Dati vite", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row_idx, column=3, columnspan=3, sticky="w", padx=10, pady=(8, 2)
        )
        row_idx += 1

        left_keys = ("vm_mat_nut", "vm_Le")
        right_keys = ("vm_mat_screw",)
        max_rows = max(len(left_keys), len(right_keys))
        for idx in range(max_rows):
            if idx < len(left_keys):
                key = left_keys[idx]
                spec = fields_by_key.get(key)
                if spec is not None:
                    add_field(spec, row_idx, 0)
                    used_keys.add(key)
            if idx < len(right_keys):
                key = right_keys[idx]
                spec = fields_by_key.get(key)
                if spec is not None:
                    add_field(spec, row_idx, 3)
                    used_keys.add(key)
            row_idx += 1

        ctk.CTkLabel(left, text="Dati funzionamento", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row_idx, column=0, columnspan=6, sticky="w", padx=10, pady=(8, 2)
        )
        row_idx += 1

        for key, col_base in (("vm_mode", 0), ("vm_T", 0), ("vm_F", 3)):
            spec = fields_by_key.get(key)
            if spec is None:
                continue
            if key == "vm_mode":
                add_field(spec, row_idx, col_base)
                used_keys.add(key)
                row_idx += 1
                continue
            add_field(spec, row_idx, col_base)
            used_keys.add(key)
        row_idx += 1

        for spec in self.fields:
            if spec.key in used_keys:
                continue
            add_field(spec, row_idx, 0)
            row_idx += 1

        return row_idx

    def _layout_gear_fields(self, left, add_field: Callable[[FieldSpec, int, int], None]) -> int:
        fields_by_key = {f.key: f for f in self.fields}
        used_keys: set[str] = set()
        row_idx = 1

        common_keys = ("m", "mn", "alpha", "beta", "sigma", "q", "aw", "x_mode")
        for key in common_keys:
            spec = fields_by_key.get(key)
            if spec is None:
                continue
            add_field(spec, row_idx, 0)
            used_keys.add(key)
            row_idx += 1

        gear1_keys: list[str] = []
        gear2_keys: list[str] = []
        for key in ("z1", "n1"):
            if key in fields_by_key and key not in used_keys:
                gear1_keys.append(key)
                used_keys.add(key)
        for key in ("z2", "n2"):
            if key in fields_by_key and key not in used_keys:
                gear2_keys.append(key)
                used_keys.add(key)

        for spec in self.fields:
            key = spec.key
            if key in used_keys:
                continue
            if key.endswith("1"):
                gear1_keys.append(key)
                used_keys.add(key)
            elif key.endswith("2"):
                gear2_keys.append(key)
                used_keys.add(key)

        if gear1_keys or gear2_keys:
            ctk.CTkLabel(left, text="Ingranaggio 1", font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=row_idx, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2)
            )
            ctk.CTkLabel(left, text="Ingranaggio 2", font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=row_idx, column=3, columnspan=3, sticky="w", padx=10, pady=(8, 2)
            )
            row_idx += 1

            max_rows = max(len(gear1_keys), len(gear2_keys))
            for idx in range(max_rows):
                if idx < len(gear1_keys):
                    add_field(fields_by_key[gear1_keys[idx]], row_idx, 0)
                if idx < len(gear2_keys):
                    add_field(fields_by_key[gear2_keys[idx]], row_idx, 3)
                row_idx += 1

        for spec in self.fields:
            if spec.key in used_keys:
                continue
            add_field(spec, row_idx, 0)
            row_idx += 1

        return row_idx

    def _on_mode_change(self, *_args) -> None:
        self._apply_mode_inputs_state()

    def _apply_default_split_60_40(self) -> None:
        paned = getattr(self, "_paned", None)
        if paned is None:
            return
        try:
            paned.update_idletasks()
            total_w = int(paned.winfo_width())
            if total_w <= 1:
                self.after(120, self._apply_default_split_60_40)
                return
            sash_x = int(total_w * 0.60)
            paned.sash_place(0, sash_x, 0)
        except Exception:
            pass

    def _has_spring_material_data_fields(self) -> bool:
        return all(k in self.vars for k in SPRING_MAT_FIELD_KEYS)

    def _load_spring_material_data_from_selection(self) -> None:
        if not self._has_spring_material_data_fields():
            return
        materiale = (self.vars.get("materiale").get() or "").strip() if self.vars.get("materiale") else ""
        if not materiale:
            return
        try:
            mat = _spring_material(materiale)
        except Exception:
            return
        self.vars["mat_e"].set(_fmt_number(mat.e_mpa, digits=3))
        self.vars["mat_g"].set(_fmt_number(mat.g_mpa, digits=3))
        self.vars["mat_sigma_amm"].set(_fmt_number(mat.sigma_amm_mpa, digits=3))
        self.vars["mat_tau_amm"].set(_fmt_number(mat.tau_amm_mpa, digits=3))

    def _on_material_change(self, *_args) -> None:
        self._load_spring_material_data_from_selection()

    def _has_beam_material_data_fields(self) -> bool:
        return all(k in self.vars for k in BEAM_MAT_FIELD_KEYS)

    def _load_beam_material_data_from_selection(self) -> None:
        if not self._has_beam_material_data_fields():
            return
        materiale = (self.vars.get("materiale_trave").get() or "").strip() if self.vars.get("materiale_trave") else ""
        if not materiale:
            return
        try:
            mat = _beam_material(materiale)
        except Exception:
            return
        self.vars["matb_e"].set(_fmt_number(mat.e_mpa, digits=3))
        self.vars["matb_g"].set(_fmt_number(mat.g_mpa, digits=3))
        self.vars["matb_sigma_amm"].set(_fmt_number(mat.sigma_amm_mpa, digits=3))
        self.vars["matb_tau_amm"].set(_fmt_number(mat.tau_amm_mpa, digits=3))

    def _on_beam_material_change(self, *_args) -> None:
        self._load_beam_material_data_from_selection()

    def _has_disc_spring_fields(self) -> bool:
        required = ("tazza_source", "tazza_std", "Do", "Di", "t", "h0")
        return all(k in self.vars for k in required)

    def _load_disc_spring_from_selection(self) -> None:
        if not self._has_disc_spring_fields():
            return
        source = (self.vars.get("tazza_source").get() or "").strip() if self.vars.get("tazza_source") else ""
        if source != DISC_SPRING_SOURCE_DB:
            return
        spring_name = (self.vars.get("tazza_std").get() or "").strip() if self.vars.get("tazza_std") else ""
        if not spring_name or spring_name == "-":
            return
        try:
            spring = _disc_spring_standard(spring_name)
        except Exception:
            return
        self.vars["Do"].set(_fmt_number(spring.do_mm, digits=3))
        self.vars["Di"].set(_fmt_number(spring.di_mm, digits=3))
        self.vars["t"].set(_fmt_number(spring.t_mm, digits=3))
        self.vars["h0"].set(_fmt_number(spring.h0_mm, digits=3))

    def _apply_disc_inputs_state(self) -> None:
        if not self._has_disc_spring_fields():
            return
        source = (self.vars.get("tazza_source").get() or "").strip()
        is_db = source == DISC_SPRING_SOURCE_DB
        self._set_input_state("tazza_std", enabled=is_db)
        self._set_input_state("Do", enabled=not is_db)
        self._set_input_state("Di", enabled=not is_db)
        self._set_input_state("t", enabled=not is_db)
        self._set_input_state("h0", enabled=not is_db)

    def _on_disc_source_change(self, *_args) -> None:
        self._load_disc_spring_from_selection()
        self._apply_disc_inputs_state()

    def _on_disc_standard_change(self, *_args) -> None:
        self._load_disc_spring_from_selection()

    def _has_screw_thread_family_fields(self) -> bool:
        required = ("vm_thread_family", "vm_thread_std")
        return all(k in self.vars for k in required) and "vm_thread_std" in self.widgets

    def _apply_screw_thread_family_filter(self) -> None:
        if not self._has_screw_thread_family_fields():
            return
        family = (self.vars.get("vm_thread_family").get() or "").strip() if self.vars.get("vm_thread_family") else ""
        options = list(_screw_thread_names_by_family(family))
        if not options:
            options = list(_screw_thread_names_by_family(SCREW_THREAD_FAMILY_CHOICES[0] if SCREW_THREAD_FAMILY_CHOICES else ""))

        std_widget = self.widgets.get("vm_thread_std")
        if isinstance(std_widget, ctk.CTkOptionMenu):
            try:
                std_widget.configure(values=options)
            except Exception:
                pass

        current_std = (self.vars.get("vm_thread_std").get() or "").strip() if self.vars.get("vm_thread_std") else ""
        if options and current_std not in options:
            self.vars["vm_thread_std"].set(options[0])

    def _has_screw_thread_fields(self) -> bool:
        required = ("vm_thread_std", "vm_d", "vm_p")
        return all(k in self.vars for k in required)

    def _load_screw_thread_from_selection(self) -> None:
        if not self._has_screw_thread_fields():
            return
        thread_name = (self.vars.get("vm_thread_std").get() or "").strip() if self.vars.get("vm_thread_std") else ""
        if not thread_name or thread_name == "-":
            return
        try:
            thread = _screw_thread_standard(thread_name)
        except Exception:
            return
        self.vars["vm_d"].set(_fmt_number(thread.d_mm, digits=3))
        self.vars["vm_p"].set(_fmt_number(thread.p_mm, digits=3))

    def _on_screw_thread_change(self, *_args) -> None:
        self._load_screw_thread_from_selection()

    def _on_screw_thread_family_change(self, *_args) -> None:
        self._apply_screw_thread_family_filter()
        self._load_screw_thread_from_selection()

    def _get_reference_entry_colors(self):
        for ref_key, ref_widget in self.widgets.items():
            if ref_key in ("f1", "f2", "F1", "F2", "vm_T", "vm_F"):
                continue
            if isinstance(ref_widget, ctk.CTkEntry):
                try:
                    return (
                        ref_widget.cget("fg_color"),
                        ref_widget.cget("border_color"),
                        ref_widget.cget("text_color"),
                    )
                except Exception:
                    break
        return self.palette.entry_bg, self.palette.border, self.palette.entry_fg

    def _set_input_state(self, key: str, enabled: bool) -> None:
        widget = self.widgets.get(key)
        label = self.input_labels.get(key)
        unit_label = self.unit_labels.get(key)
        base_label = self.base_label_texts.get(key, key)
        active_fg, active_border, active_text = self._get_reference_entry_colors()

        if label is not None:
            if enabled:
                label.configure(text=base_label, text_color=self.palette.fg)
            else:
                label.configure(text=f"{base_label} [DISATTIVO]", text_color=self.palette.fg)
        if unit_label is not None:
            unit_label.configure(text_color=self.palette.muted_fg)

        if isinstance(widget, ctk.CTkOptionMenu):
            try:
                widget.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass
            return

        if not isinstance(widget, ctk.CTkEntry):
            return
        try:
            if enabled:
                widget.configure(
                    state="normal",
                    fg_color=active_fg,
                    border_color=active_border,
                    text_color=active_text,
                )
            else:
                disabled_bg = self.palette.disabled_entry_bg
                widget.configure(
                    state="disabled",
                    fg_color=disabled_bg,
                    border_color=active_border,
                    text_color=active_text,
                )
        except Exception:
            pass

    def _is_input_enabled(self, key: str) -> bool:
        widget = self.widgets.get(key)
        if not isinstance(widget, ctk.CTkEntry):
            return True
        try:
            return str(widget.cget("state")).lower() != "disabled"
        except Exception:
            return True

    def _apply_mode_inputs_state(self) -> None:
        mode_var = self.vars.get("modo_calcolo")
        if mode_var is not None:
            mode = (mode_var.get() or "").strip()
            if mode == SPRING_CALC_MODE_DEF_FROM_FORCE:
                self._set_input_state("f1", enabled=False)
                self._set_input_state("f2", enabled=False)
                self._set_input_state("F1", enabled=True)
                self._set_input_state("F2", enabled=True)
            else:
                self._set_input_state("f1", enabled=True)
                self._set_input_state("f2", enabled=True)
                self._set_input_state("F1", enabled=False)
                self._set_input_state("F2", enabled=False)
        vm_mode_var = self.vars.get("vm_mode")
        if vm_mode_var is not None:
            vm_mode = (vm_mode_var.get() or "").strip()
            if vm_mode == SCREW_VM_MODE_FORCE_FROM_TORQUE:
                self._set_input_state("vm_T", enabled=True)
                self._set_input_state("vm_F", enabled=False)
            elif vm_mode == SCREW_VM_MODE_TORQUE_FROM_FORCE:
                self._set_input_state("vm_T", enabled=False)
                self._set_input_state("vm_F", enabled=True)
        self._apply_disc_inputs_state()

    def _parse_values(self) -> dict[str, CalcValue]:
        parsed: dict[str, CalcValue] = {}
        for spec in self.fields:
            raw = (self.vars[spec.key].get() or "").strip()
            if spec.field_type in ("choice", "radio"):
                if not raw:
                    raise ValueError(f"Compila {spec.label}.")
                parsed[spec.key] = raw
            elif spec.field_type == "int":
                parsed[spec.key] = _as_int(raw, spec.label)
            elif spec.field_type == "float_optional":
                if not self._is_input_enabled(spec.key):
                    parsed[spec.key] = None
                    continue
                parsed[spec.key] = None if not raw else _as_float(raw, spec.label)
            else:
                parsed[spec.key] = _as_float(raw, spec.label)
        return parsed

    def _show_results(self, rows: CalcRows) -> None:
        _render_results_colored(self.txt_results, rows, self.palette)

    def _on_calculate(self) -> None:
        try:
            values = self._parse_values()
            rows = self.calc_fn(values)
            self._show_results(rows)
            global_outcome = ""
            for label, value in rows:
                if (label or "").strip().lower() == "esito globale":
                    global_outcome = str(value or "").strip().upper()
                    break
            if global_outcome == "NON OK":
                self.var_status.set("Calcolo completato: verifica globale NON OK.")
                self.lbl_status.configure(text_color=self.palette.err)
            elif global_outcome == "OK":
                self.var_status.set("Calcolo completato: verifica globale OK.")
                self.lbl_status.configure(text_color=self.palette.ok)
            else:
                self.var_status.set("Calcolo completato.")
                self.lbl_status.configure(text_color=self.palette.ok)
        except Exception as exc:
            self.var_status.set(str(exc))
            self.lbl_status.configure(text_color=self.palette.err)

    def _on_reset(self) -> None:
        for key, default in self.defaults.items():
            self.vars[key].set(default)
        self._load_spring_material_data_from_selection()
        self._load_beam_material_data_from_selection()
        self._on_screw_thread_family_change()
        self._on_disc_source_change()
        self._apply_mode_inputs_state()
        self.txt_results.configure(state="normal")
        self.txt_results.delete("1.0", "end")
        self.txt_results.configure(state="disabled")
        self.var_status.set("Inserisci dati e premi CALCOLA.")
        self.lbl_status.configure(text_color=self.palette.muted_fg)


class GearCombinedPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        group_title: str,
        calculators: Sequence[tuple[str, str, str, Sequence[FieldSpec], CalcFn]],
        palette: Palette,
    ) -> None:
        super().__init__(master)
        self.group_title = group_title
        self.calculators = tuple(calculators)
        self.palette = palette
        mode_values = [mode_label for mode_label, *_ in self.calculators]
        self.var_mode = ctk.StringVar(value=mode_values[0] if mode_values else "")
        self.panels_by_mode: dict[str, CalculatorPanel] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text=f"{self.group_title} - Tipo dentatura").grid(
            row=0, column=0, sticky="w", padx=(10, 8), pady=10
        )
        self.mode_menu = ctk.CTkOptionMenu(top, values=mode_values, variable=self.var_mode, command=self._on_mode_change)
        self.mode_menu.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=10)

        self.host = ctk.CTkFrame(self)
        self.host.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.host.grid_columnconfigure(0, weight=1)
        self.host.grid_rowconfigure(0, weight=1)

        for mode_label, calc_title, description, fields, calc_fn in self.calculators:
            panel = CalculatorPanel(self.host, calc_title, description, fields, calc_fn, self.palette)
            panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            self.panels_by_mode[mode_label] = panel

        self._set_active_mode()

    def _on_mode_change(self, _selected: str) -> None:
        self._set_active_mode()

    def _set_active_mode(self) -> None:
        mode = (self.var_mode.get() or "").strip()
        for key, panel in self.panels_by_mode.items():
            if key == mode:
                panel.grid()
            else:
                panel.grid_remove()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.spring_db = SPRING_DB
        self.beam_db = BEAM_DB
        self.tol_db = TOL_DB
        self.screw_db = SCREW_DB
        self.spring_db.ensure_seeded()
        self.beam_db.ensure_seeded()
        self.tol_db.ensure_seeded()
        self.screw_db.ensure_seeded()
        self.spring_material_names = self.spring_db.list_names()
        self.beam_material_names = self.beam_db.list_names()
        self.beam_section_names = self.beam_db.list_section_names()
        self.tol_material_names = self.tol_db.list_material_names()
        self.tol_hole_positions = self.tol_db.list_iso_positions("HOLE")
        self.tol_shaft_positions = self.tol_db.list_iso_positions("SHAFT")
        self.tol_iso_grades = self.tol_db.list_iso_grades("HOLE")
        self.screw_thread_names = self.screw_db.list_thread_names()
        self.screw_material_names = self.screw_db.list_material_names()
        if not self.spring_material_names:
            raise RuntimeError("DB materiali molle vuoto.")
        if not self.beam_material_names:
            raise RuntimeError("DB materiali travi vuoto.")
        if not self.beam_section_names:
            raise RuntimeError("DB sezioni standard travi vuoto.")
        if not self.tol_material_names:
            raise RuntimeError("DB materiali tolleranze vuoto.")
        if not self.tol_hole_positions or not self.tol_shaft_positions or not self.tol_iso_grades:
            raise RuntimeError("DB tolleranze ISO foro/albero vuoto.")
        if not self.screw_thread_names:
            raise RuntimeError("DB filettature vite-madrevite vuoto.")
        if not self.screw_material_names:
            raise RuntimeError("DB materiali vite-madrevite vuoto.")
        self.disc_spring_names = self.spring_db.list_disc_spring_names()

        self.palette = apply_style(dark=True)
        self.title(f"{APP_NAME} v{APP_VERSION} - {STYLE_NAME}")
        self.geometry("1550x900")
        self.minsize(1250, 720)
        self.configure(fg_color=self.palette.bg)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=APP_NAME, font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 2)
        )
        ctk.CTkLabel(
            top,
            text=(
                "Calcoli preliminari di ingranaggi, molle, travi e tolleranze. "
                f"Versione {APP_VERSION}"
            ),
            text_color=self.palette.muted_fg,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        main_tabs = ctk.CTkTabview(self)
        main_tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)

        self._build_gear_category(main_tabs.add("Ingranaggi"), GEAR_CALCS)
        self._build_category(
            main_tabs.add("Molle"),
            get_spring_calcs(self.spring_material_names, self.disc_spring_names),
        )
        self._build_category(main_tabs.add("Travi"), get_beam_calcs(self.beam_material_names))
        self._build_category(main_tabs.add("Tolleranze"), TOL_CALCS)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            footer,
            text="Nota: formule orientate a verifica rapida preliminare.",
            text_color=self.palette.warn,
        ).pack(anchor="w")

    def _build_gear_category(self, container, calculators: Sequence[tuple[str, str, Sequence[FieldSpec], CalcFn]]) -> None:
        grouped_tabs = ctk.CTkTabview(container)
        grouped_tabs.pack(fill="both", expand=True, padx=8, pady=8)

        calculators_by_title = {
            title: (description, fields, calc_fn) for title, description, fields, calc_fn in calculators
        }
        grouped_titles: set[str] = set()

        for group_title, group_tabs in GEAR_TAB_GROUPS:
            group_entries = [
                (tab_label, calc_title, *calculators_by_title[calc_title])
                for tab_label, calc_title in group_tabs
                if calc_title in calculators_by_title
            ]
            if not group_entries:
                continue
            grouped_titles.update(calc_title for _tab_label, calc_title, *_ in group_entries)

            group_container = grouped_tabs.add(group_title)
            panel = GearCombinedPanel(group_container, group_title, group_entries, self.palette)
            panel.pack(fill="both", expand=True, padx=6, pady=6)

        for title, description, fields, calc_fn in calculators:
            if title in grouped_titles:
                continue
            tab = grouped_tabs.add(title)
            panel = self._create_panel(tab, title, description, fields, calc_fn)
            panel.pack(fill="both", expand=True, padx=6, pady=6)

    def _create_panel(
        self,
        tab,
        title: str,
        description: str,
        fields: Sequence[FieldSpec],
        calc_fn: CalcFn,
    ):
        if title == "Flessione":
            return BeamBendingPanel(tab, self.palette, self.beam_material_names, self.beam_section_names)
        if title == "Torsione":
            return BeamTorsionPanel(tab, self.palette, self.beam_material_names)
        if title == "Accoppiamento foro/albero":
            return FitTolerancePanel(
                tab,
                self.palette,
                self.tol_material_names,
                self.tol_hole_positions,
                self.tol_shaft_positions,
                self.tol_iso_grades,
            )
        return CalculatorPanel(tab, title, description, fields, calc_fn, self.palette)

    def _build_category(self, container, calculators: Sequence[tuple[str, str, Sequence[FieldSpec], CalcFn]]) -> None:
        subtabs = ctk.CTkTabview(container)
        subtabs.pack(fill="both", expand=True, padx=8, pady=8)

        for title, description, fields, calc_fn in calculators:
            tab = subtabs.add(title)
            panel = self._create_panel(tab, title, description, fields, calc_fn)
            panel.pack(fill="both", expand=True, padx=6, pady=6)


def main() -> None:
    try:
        App().mainloop()
    except Exception as exc:
        messagebox.showerror("Errore", f"Errore avvio applicazione: {exc}")
