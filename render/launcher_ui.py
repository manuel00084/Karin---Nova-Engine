"""Karin VTuber Launcher UI — graphical backend selector with tabs."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import subprocess
import tempfile
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.backends import list_backends
from render.tools import translate as jptrans
from render.tools import dedup
from render.tools import optimize_tex
from render.tools import strip_bones, copy_blendshapes, prune_morphs
from render.tools import add_virtual_morphs

BACKEND_APIS = {
    "nova": ["D3D12", "Vulkan", "Metal"],
}


class LauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Karin VTuber Launcher")
        self.root.geometry("680x720")
        self.root.resizable(False, True)
        self.root.minsize(680, 720)

        backends = list_backends()

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Karin — Nova Engine 3D",
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 6))

        # ── Bottom buttons (pack FIRST so they stay visible) ──
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(main, textvariable=self.status_var,
                  font=("Segoe UI", 8)).pack(side="bottom")

        f_bottom = ttk.Frame(main)
        f_bottom.pack(side="bottom", fill="x", pady=(4, 3))
        self.launch_btn = ttk.Button(
            f_bottom, text="Iniciar", command=self._launch)
        self.launch_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        ttk.Button(
            f_bottom, text="Guardar config",
            command=self._save_config_dialog).pack(side="right", fill="x", expand=True, padx=(3, 0))

        # ── Tabs ──
        notebook = ttk.Notebook(main)
        notebook.pack(fill="both", expand=True, pady=(0, 6))

        # ===== Tab: Model =====
        tab_model = ttk.Frame(notebook, padding=8)
        notebook.add(tab_model, text="  Modelo  ")

        f_model = ttk.Frame(tab_model)
        f_model.pack(fill="x", pady=3)
        ttk.Label(f_model, text="Modelo:", width=10, anchor="w").pack(side="left")
        self.model_var = tk.StringVar()
        ttk.Entry(f_model, textvariable=self.model_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f_model, text="Examinar", command=self._browse).pack(side="right")

        f_backend = ttk.Frame(tab_model)
        f_backend.pack(fill="x", pady=3)
        ttk.Label(f_backend, text="Render:", width=10, anchor="w").pack(side="left")
        self.backend_var = tk.StringVar(value=backends[0] if backends else "")
        self.backend_combo = ttk.Combobox(
            f_backend, textvariable=self.backend_var, values=backends,
            state="readonly", width=12)
        self.backend_combo.pack(side="left", padx=(0, 15))
        self.backend_combo.bind("<<ComboboxSelected>>", self._on_backend_change)
        ttk.Label(f_backend, text="API:").pack(side="left")
        self.api_var = tk.StringVar()
        self.api_combo = ttk.Combobox(
            f_backend, textvariable=self.api_var, state="readonly", width=12)
        self.api_combo.pack(side="left", padx=(5, 0))
        self._update_api_list()

        f_res = ttk.Frame(tab_model)
        f_res.pack(fill="x", pady=3)
        ttk.Label(f_res, text="Resolucion:", width=10, anchor="w").pack(side="left")
        self.res_w = tk.StringVar(value="1280")
        self.res_h = tk.StringVar(value="720")
        ttk.Entry(f_res, textvariable=self.res_w, width=6).pack(side="left")
        ttk.Label(f_res, text="x").pack(side="left", padx=3)
        ttk.Entry(f_res, textvariable=self.res_h, width=6).pack(side="left", padx=(0, 15))
        ttk.Label(f_res, text="FPS:").pack(side="left")
        self.fps_var = tk.StringVar(value="60")
        ttk.Combobox(f_res, textvariable=self.fps_var,
                     values=["15", "30", "60"],
                     state="readonly", width=5).pack(side="left", padx=(5, 0))

        f_render_mode = ttk.Frame(tab_model)
        f_render_mode.pack(fill="x", pady=3)
        ttk.Label(f_render_mode, text="Modo Render:", width=10, anchor="w").pack(side="left")
        self.render_mode_var = tk.StringVar(value="cpu+gpu")
        ttk.Combobox(f_render_mode, textvariable=self.render_mode_var,
                     values=["cpu", "gpu-hw", "cpu+gpu", "software"],
                     state="readonly", width=14).pack(side="left", padx=(0, 15))
        ttk.Label(f_render_mode, text="CPU solo | GPU hw | CPU+GPU | Software",
                  font=("Segoe UI", 7)).pack(side="left")

        # Presets
        f_preset = ttk.Frame(tab_model)
        f_preset.pack(fill="x", pady=3)
        ttk.Label(f_preset, text="Presets:", width=10, anchor="w").pack(side="left")
        self._presets_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "presets")
        os.makedirs(self._presets_dir, exist_ok=True)
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            f_preset, textvariable=self.preset_var,
            values=self._list_presets(), width=18)
        self.preset_combo.pack(side="left", padx=(0, 5))
        ttk.Button(f_preset, text="Cargar",
                   command=self._load_preset).pack(side="left", padx=2)
        ttk.Button(f_preset, text="Guardar",
                   command=self._save_preset).pack(side="left", padx=2)
        ttk.Button(f_preset, text="Eliminar",
                   command=self._delete_preset).pack(side="left", padx=2)

        f_chk = ttk.Frame(tab_model)
        f_chk.pack(fill="x", pady=3)
        ttk.Label(f_chk, text="Opciones:", width=10, anchor="w").pack(side="left")
        self.chroma_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_chk, text="Chroma Key", variable=self.chroma_var).pack(side="left")
        self.transparent_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_chk, text="Transparent BG", variable=self.transparent_var).pack(side="left")

        f_bg = ttk.Frame(tab_model)
        f_bg.pack(fill="x", pady=2)
        ttk.Label(f_bg, text="Fondo:", width=10, anchor="w").pack(side="left")
        self.bg_var = tk.StringVar()
        ttk.Entry(f_bg, textvariable=self.bg_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f_bg, text="Examinar",
                   command=self._browse_bg).pack(side="right")

        f_acc = ttk.Frame(tab_model)
        f_acc.pack(fill="x", pady=2)
        ttk.Label(f_acc, text="Accesorio:", width=10, anchor="w").pack(side="left")
        self.acc_var = tk.StringVar()
        ttk.Entry(f_acc, textvariable=self.acc_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f_acc, text="Examinar",
                   command=self._browse_acc).pack(side="right")
        ttk.Label(f_acc, text="Hueso:").pack(side="left", padx=(5, 0))
        self.acc_bone_var = tk.StringVar(value="Head")
        ttk.Entry(f_acc, textvariable=self.acc_bone_var, width=10).pack(side="left", padx=(3, 0))

        # Recent models
        self._load_recent(tab_model)



        # ===== Tab: Voz/Cam =====
        tab_voice = ttk.Frame(notebook, padding=8)
        notebook.add(tab_voice, text="  Voz/Cam  ")

        f_audio = ttk.LabelFrame(tab_voice, text="  Audio + Lip Sync  ", padding=8)
        f_audio.pack(fill="x", pady=3)

        f_audio_top = ttk.Frame(f_audio)
        f_audio_top.pack(fill="x", pady=2)
        ttk.Label(f_audio_top, text="Archivo:", width=8, anchor="w").pack(side="left")
        self.audio_file_var = tk.StringVar()
        ttk.Entry(f_audio_top, textvariable=self.audio_file_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f_audio_top, text="Examinar",
                   command=self._browse_audio).pack(side="right")

        self.audio_auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_audio, text="Reproducir al iniciar",
                        variable=self.audio_auto_var).pack(anchor="w", pady=2)

        ttk.Separator(f_audio, orient="horizontal").pack(fill="x", pady=4)

        self.mic_lipsync_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_audio, text="Micrófono Lip Sync ([) al iniciar",
                        variable=self.mic_lipsync_var).pack(anchor="w", pady=2)

        f_webcam = ttk.LabelFrame(tab_voice, text="  Webcam Face Tracking  ", padding=8)
        f_webcam.pack(fill="x", pady=3)

        f_webcam_top = ttk.Frame(f_webcam)
        f_webcam_top.pack(fill="x", pady=2)
        ttk.Label(f_webcam_top, text="Camara ID:").pack(side="left")
        self.webcam_id_var = tk.StringVar(value="0")
        ttk.Spinbox(f_webcam_top, from_=0, to=9, textvariable=self.webcam_id_var,
                    width=4).pack(side="left", padx=(5, 15))
        self.webcam_auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_webcam_top, text="Iniciar al arrancar (N)",
                        variable=self.webcam_auto_var).pack(side="left")

        f_webcam_cal = ttk.Frame(f_webcam)
        f_webcam_cal.pack(fill="x", pady=2)
        r_cal1 = ttk.Frame(f_webcam_cal); r_cal1.pack(fill="x", pady=1)
        ttk.Label(r_cal1, text="Smoothing:", width=12, anchor="w").pack(side="left")
        self.webcam_smoothing_var = tk.DoubleVar(value=8.0)
        ttk.Scale(r_cal1, from_=1, to=30, orient="horizontal",
                  variable=self.webcam_smoothing_var, length=80).pack(side="left", padx=(0, 10))
        ttk.Label(r_cal1, text="Eye Sens:").pack(side="left")
        self.webcam_eye_sens_var = tk.DoubleVar(value=3.0)
        ttk.Scale(r_cal1, from_=0.5, to=8, orient="horizontal",
                  variable=self.webcam_eye_sens_var, length=80).pack(side="left", padx=(5, 0))

        r_cal2 = ttk.Frame(f_webcam_cal); r_cal2.pack(fill="x", pady=1)
        ttk.Label(r_cal2, text="Mouth Div:", width=12, anchor="w").pack(side="left")
        self.webcam_mouth_sens_var = tk.DoubleVar(value=30.0)
        ttk.Scale(r_cal2, from_=10, to=80, orient="horizontal",
                  variable=self.webcam_mouth_sens_var, length=80).pack(side="left", padx=(0, 10))
        ttk.Label(r_cal2, text="Mouth Gain:").pack(side="left")
        self.webcam_mouth_gain_var = tk.DoubleVar(value=1.5)
        ttk.Scale(r_cal2, from_=0.5, to=4, orient="horizontal",
                  variable=self.webcam_mouth_gain_var, length=80).pack(side="left", padx=(5, 0))

        r_cal3 = ttk.Frame(f_webcam_cal); r_cal3.pack(fill="x", pady=1)
        ttk.Label(r_cal3, text="Head Sens:", width=12, anchor="w").pack(side="left")
        self.webcam_head_sens_var = tk.DoubleVar(value=1.0)
        ttk.Scale(r_cal3, from_=0.2, to=3, orient="horizontal",
                  variable=self.webcam_head_sens_var, length=80).pack(side="left", padx=(0, 10))
        self.webcam_flip_x_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_cal3, text="Mirror X", variable=self.webcam_flip_x_var).pack(side="left", padx=(10, 0))

        r_cal4 = ttk.Frame(f_webcam_cal); r_cal4.pack(fill="x", pady=1)
        ttk.Label(r_cal4, text="Pitch Offset:", width=12, anchor="w").pack(side="left")
        self.webcam_pitch_var = tk.DoubleVar(value=0.0)
        ttk.Scale(r_cal4, from_=-1.5, to=1.5, orient="horizontal",
                  variable=self.webcam_pitch_var, length=80).pack(side="left", padx=(0, 10))
        ttk.Label(r_cal4, text="Yaw Offset:").pack(side="left")
        self.webcam_yaw_var = tk.DoubleVar(value=0.0)
        ttk.Scale(r_cal4, from_=-1.5, to=1.5, orient="horizontal",
                  variable=self.webcam_yaw_var, length=80).pack(side="left", padx=(5, 0))

        # ===== Tab: Gráficos =====
        tab_gfx = ttk.Frame(notebook, padding=8)
        notebook.add(tab_gfx, text="  Gráficos  ")

        gfx_canvas = tk.Canvas(tab_gfx, borderwidth=0, highlightthickness=0, bg="#1e1e1e")
        gfx_scroll = ttk.Scrollbar(tab_gfx, orient="vertical", command=gfx_canvas.yview)
        gfx_inner = ttk.Frame(gfx_canvas)
        gfx_canvas.configure(yscrollcommand=gfx_scroll.set)
        gfx_scroll.pack(side="right", fill="y")
        gfx_canvas.pack(side="left", fill="both", expand=True)
        gfx_inner.bind("<Configure>",
                       lambda e: gfx_canvas.configure(scrollregion=gfx_canvas.bbox("all")))
        gfx_canvas.create_window((0, 0), window=gfx_inner, anchor="nw")

        # ── Sombreado ──
        f_shade = ttk.LabelFrame(gfx_inner, text="  Sombreado  ", padding=6)
        f_shade.pack(fill="x", pady=3)
        r1 = ttk.Frame(f_shade); r1.pack(fill="x", pady=1)
        ttk.Label(r1, text="Toon:", width=12, anchor="w").pack(side="left")
        self.gfx_toon_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="On", variable=self.gfx_toon_var).pack(side="left")
        ttk.Label(r1, text="  Mirar al mouse:").pack(side="left", padx=(10, 0))
        self.gfx_look_mouse_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r1, text="On", variable=self.gfx_look_mouse_var).pack(side="left")

        r1a = ttk.Frame(f_shade); r1a.pack(fill="x", pady=1)
        ttk.Label(r1a, text="Anim:", width=12, anchor="w").pack(side="left")
        self.gfx_idle_anim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r1a, text="Idle", variable=self.gfx_idle_anim_var).pack(side="left", padx=(0, 10))
        self.gfx_leg_ik_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r1a, text="Leg IK", variable=self.gfx_leg_ik_var).pack(side="left", padx=(0, 10))
        self.gfx_head_ik_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r1a, text="Head IK", variable=self.gfx_head_ik_var).pack(side="left")

        r1b = ttk.Frame(f_shade); r1b.pack(fill="x", pady=1)
        ttk.Label(r1b, text="Toon Cutoff:", width=12, anchor="w").pack(side="left")
        self.gfx_toon_cutoff_var = tk.DoubleVar(value=0.3)
        ttk.Scale(r1b, from_=0, to=1, orient="horizontal",
                  variable=self.gfx_toon_cutoff_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r1b, text="Smooth:").pack(side="left")
        self.gfx_toon_smooth_var = tk.DoubleVar(value=0.08)
        ttk.Scale(r1b, from_=0, to=0.5, orient="horizontal",
                  variable=self.gfx_toon_smooth_var, length=100).pack(side="left", padx=(5, 0))

        r1c = ttk.Frame(f_shade); r1c.pack(fill="x", pady=1)
        ttk.Label(r1c, text="Shade Shift:", width=12, anchor="w").pack(side="left")
        self.gfx_shade_shift_var = tk.DoubleVar(value=0.0)
        ttk.Scale(r1c, from_=-1, to=1, orient="horizontal",
                  variable=self.gfx_shade_shift_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r1c, text="Shade Color:").pack(side="left")
        self.gfx_shade_color_var = tk.StringVar(value="0.55,0.42,0.48")
        ttk.Entry(r1c, textvariable=self.gfx_shade_color_var, width=16).pack(side="left")

        # ── Iluminación ──
        f_light = ttk.LabelFrame(gfx_inner, text="  Iluminación  ", padding=6)
        f_light.pack(fill="x", pady=3)

        r2a = ttk.Frame(f_light); r2a.pack(fill="x", pady=1)
        ttk.Label(r2a, text="Ambient R/G/B:", width=14, anchor="w").pack(side="left")
        self.gfx_amb_r_var = tk.StringVar(value="0.3")
        ttk.Entry(r2a, textvariable=self.gfx_amb_r_var, width=5).pack(side="left", padx=(0, 2))
        self.gfx_amb_g_var = tk.StringVar(value="0.3")
        ttk.Entry(r2a, textvariable=self.gfx_amb_g_var, width=5).pack(side="left", padx=2)
        self.gfx_amb_b_var = tk.StringVar(value="0.35")
        ttk.Entry(r2a, textvariable=self.gfx_amb_b_var, width=5).pack(side="left", padx=2)

        r2b = ttk.Frame(f_light); r2b.pack(fill="x", pady=1)
        ttk.Label(r2b, text="Main Light H/P:", width=14, anchor="w").pack(side="left")
        self.gfx_main_h_var = tk.StringVar(value="180")
        ttk.Entry(r2b, textvariable=self.gfx_main_h_var, width=5).pack(side="left", padx=(0, 2))
        self.gfx_main_p_var = tk.StringVar(value="20")
        ttk.Entry(r2b, textvariable=self.gfx_main_p_var, width=5).pack(side="left", padx=2)

        r2d = ttk.Frame(f_light); r2d.pack(fill="x", pady=1)
        ttk.Label(r2d, text="IBL Intensity:", width=14, anchor="w").pack(side="left")
        self.gfx_ibl_int_var = tk.DoubleVar(value=0.5)
        ttk.Scale(r2d, from_=0, to=2, orient="horizontal",
                  variable=self.gfx_ibl_int_var, length=80).pack(side="left", padx=(0, 10))

        r2f = ttk.Frame(f_light); r2f.pack(fill="x", pady=1)
        ttk.Label(r2f, text="Hemi Sky:", width=14, anchor="w").pack(side="left")
        self.gfx_hemi_sky_r_var = tk.StringVar(value="0.4")
        ttk.Entry(r2f, textvariable=self.gfx_hemi_sky_r_var, width=5).pack(side="left", padx=(0, 2))
        self.gfx_hemi_sky_g_var = tk.StringVar(value="0.5")
        ttk.Entry(r2f, textvariable=self.gfx_hemi_sky_g_var, width=5).pack(side="left", padx=2)
        self.gfx_hemi_sky_b_var = tk.StringVar(value="0.7")
        ttk.Entry(r2f, textvariable=self.gfx_hemi_sky_b_var, width=5).pack(side="left", padx=2)
        ttk.Label(r2f, text="  Ground:").pack(side="left", padx=(10, 0))
        self.gfx_hemi_gnd_r_var = tk.StringVar(value="0.3")
        ttk.Entry(r2f, textvariable=self.gfx_hemi_gnd_r_var, width=5).pack(side="left", padx=(5, 2))
        self.gfx_hemi_gnd_g_var = tk.StringVar(value="0.25")
        ttk.Entry(r2f, textvariable=self.gfx_hemi_gnd_g_var, width=5).pack(side="left", padx=2)
        self.gfx_hemi_gnd_b_var = tk.StringVar(value="0.2")
        ttk.Entry(r2f, textvariable=self.gfx_hemi_gnd_b_var, width=5).pack(side="left", padx=2)
        r2g = ttk.Frame(f_light); r2g.pack(fill="x", pady=1)
        ttk.Label(r2g, text="Hemi Intensity:", width=14, anchor="w").pack(side="left")
        self.gfx_hemi_int_var = tk.DoubleVar(value=0.5)
        ttk.Scale(r2g, from_=0, to=2, orient="horizontal",
                  variable=self.gfx_hemi_int_var, length=100).pack(side="left")

        # ── Post-Process ──
        f_pp = ttk.LabelFrame(gfx_inner, text="  Post-Process  ", padding=6)
        f_pp.pack(fill="x", pady=3)

        r3a = ttk.Frame(f_pp); r3a.pack(fill="x", pady=1)
        self.gfx_fxaa_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r3a, text="FXAA", variable=self.gfx_fxaa_var).pack(side="left", padx=(0, 15))
        self.gfx_bloom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r3a, text="Bloom", variable=self.gfx_bloom_var).pack(side="left", padx=(0, 15))
        self.gfx_edge_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r3a, text="Edge Detect", variable=self.gfx_edge_var).pack(side="left", padx=(0, 15))
        self.gfx_device_overlay_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r3a, text="Keyboard/Mouse", variable=self.gfx_device_overlay_var).pack(side="left")

        r3e = ttk.Frame(f_pp); r3e.pack(fill="x", pady=1)
        ttk.Label(r3e, text="Bloom Threshold:", width=14, anchor="w").pack(side="left")
        self.gfx_bloom_thresh_var = tk.DoubleVar(value=0.8)
        ttk.Scale(r3e, from_=0, to=2, orient="horizontal",
                  variable=self.gfx_bloom_thresh_var, length=80).pack(side="left", padx=(0, 10))
        ttk.Label(r3e, text="Intensity:").pack(side="left")
        self.gfx_bloom_int_var = tk.DoubleVar(value=0.4)
        ttk.Scale(r3e, from_=0, to=2, orient="horizontal",
                  variable=self.gfx_bloom_int_var, length=80).pack(side="left", padx=(5, 0))
        r3f = ttk.Frame(f_pp); r3f.pack(fill="x", pady=1)
        ttk.Label(r3f, text="Bloom Radius:", width=14, anchor="w").pack(side="left")
        self.gfx_bloom_radius_var = tk.DoubleVar(value=4.0)
        ttk.Scale(r3f, from_=0, to=16, orient="horizontal",
                  variable=self.gfx_bloom_radius_var, length=120).pack(side="left")

        # ── FSR / Upscaling ──
        f_fsr = ttk.LabelFrame(gfx_inner, text="  FSR / Upscaling  ", padding=6)
        f_fsr.pack(fill="x", pady=3)
        r4a = ttk.Frame(f_fsr); r4a.pack(fill="x", pady=1)
        ttk.Label(r4a, text="FSR Mode:", width=10, anchor="w").pack(side="left")
        self.gfx_fsr_var = tk.StringVar(value="Off")
        ttk.Combobox(r4a, textvariable=self.gfx_fsr_var,
                     values=["Off", "Ultra Perf", "Perf", "Balanced", "Quality"],
                     state="readonly", width=12).pack(side="left", padx=(0, 15))
        ttk.Label(r4a, text="Sharpness:").pack(side="left")
        self.gfx_fsr_sharp_var = tk.DoubleVar(value=0.2)
        ttk.Scale(r4a, from_=0, to=1, orient="horizontal",
                  variable=self.gfx_fsr_sharp_var, length=80).pack(side="left", padx=(5, 0))
        r4b = ttk.Frame(f_fsr); r4b.pack(fill="x", pady=1)
        ttk.Label(r4b, text="Output Res:", width=10, anchor="w").pack(side="left")
        self.gfx_out_res_var = tk.StringVar(value="1080p")
        ttk.Combobox(r4b, textvariable=self.gfx_out_res_var,
                     values=["720p", "1080p"], state="readonly", width=8).pack(side="left", padx=(0, 15))
        ttk.Label(r4b, text="Texturas:").pack(side="left")
        self.gfx_tex_qual_var = tk.StringVar(value="Medio (512px)")
        ttk.Combobox(r4b, textvariable=self.gfx_tex_qual_var,
                     values=["Bajo (128px)", "Medio (512px)", "Alto (original)"],
                     state="readonly", width=15).pack(side="left")

        # ── Outline ──
        f_out = ttk.LabelFrame(gfx_inner, text="  Outline / Bordes  ", padding=6)
        f_out.pack(fill="x", pady=3)
        r5a = ttk.Frame(f_out); r5a.pack(fill="x", pady=1)
        ttk.Label(r5a, text="Width:", width=8, anchor="w").pack(side="left")
        self.gfx_outline_w_var = tk.DoubleVar(value=0.005)
        ttk.Scale(r5a, from_=0, to=0.1, orient="horizontal",
                  variable=self.gfx_outline_w_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r5a, text="Color R/G/B/A:").pack(side="left")
        self.gfx_outline_r_var = tk.StringVar(value="0.0")
        ttk.Entry(r5a, textvariable=self.gfx_outline_r_var, width=4).pack(side="left", padx=(5, 2))
        self.gfx_outline_g_var = tk.StringVar(value="0.0")
        ttk.Entry(r5a, textvariable=self.gfx_outline_g_var, width=4).pack(side="left", padx=2)
        self.gfx_outline_b_var = tk.StringVar(value="0.0")
        ttk.Entry(r5a, textvariable=self.gfx_outline_b_var, width=4).pack(side="left", padx=2)
        self.gfx_outline_a_var = tk.StringVar(value="0.0")
        ttk.Entry(r5a, textvariable=self.gfx_outline_a_var, width=4).pack(side="left", padx=2)

        r5b = ttk.Frame(f_out); r5b.pack(fill="x", pady=1)
        ttk.Label(r5b, text="Min Dist:", width=8, anchor="w").pack(side="left")
        self.gfx_out_min_dist_var = tk.DoubleVar(value=1.0)
        ttk.Scale(r5b, from_=0, to=10, orient="horizontal",
                  variable=self.gfx_out_min_dist_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r5b, text="Max Dist:").pack(side="left")
        self.gfx_out_max_dist_var = tk.DoubleVar(value=12.0)
        ttk.Scale(r5b, from_=0, to=20, orient="horizontal",
                  variable=self.gfx_out_max_dist_var, length=100).pack(side="left", padx=(5, 0))

        r5c = ttk.Frame(f_out); r5c.pack(fill="x", pady=1)
        ttk.Label(r5c, text="Normal Strength:", width=14, anchor="w").pack(side="left")
        self.gfx_edge_norm_var = tk.DoubleVar(value=5.0)
        ttk.Scale(r5c, from_=0, to=20, orient="horizontal",
                  variable=self.gfx_edge_norm_var, length=80).pack(side="left", padx=(0, 10))
        ttk.Label(r5c, text="Depth Strength:").pack(side="left")
        self.gfx_edge_depth_var = tk.DoubleVar(value=5.0)
        ttk.Scale(r5c, from_=0, to=20, orient="horizontal",
                  variable=self.gfx_edge_depth_var, length=80).pack(side="left", padx=(5, 0))

        # ── OSC Output ──
        f_osc = ttk.LabelFrame(gfx_inner, text="  OSC Output  ", padding=6)
        f_osc.pack(fill="x", pady=3)
        r_osc1 = ttk.Frame(f_osc); r_osc1.pack(fill="x", pady=1)
        self.gfx_osc_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_osc1, text="OSC Enabled (O key)", variable=self.gfx_osc_var).pack(side="left", padx=(0, 15))
        ttk.Label(r_osc1, text="Address:").pack(side="left")
        self.gfx_osc_addr_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(r_osc1, textvariable=self.gfx_osc_addr_var, width=14).pack(side="left", padx=(5, 10))
        ttk.Label(r_osc1, text="Port:").pack(side="left")
        self.gfx_osc_port_var = tk.IntVar(value=9000)
        ttk.Entry(r_osc1, textvariable=self.gfx_osc_port_var, width=6).pack(side="left", padx=(5, 0))
        r_osc2 = ttk.Frame(f_osc); r_osc2.pack(fill="x", pady=1)
        ttk.Label(r_osc2, text="Rate (fps):", width=12, anchor="w").pack(side="left")
        self.gfx_osc_rate_var = tk.IntVar(value=30)
        ttk.Scale(r_osc2, from_=5, to=60, orient="horizontal",
                  variable=self.gfx_osc_rate_var, length=120).pack(side="left", padx=(5, 0))
        r_osc3 = ttk.Frame(f_osc); r_osc3.pack(fill="x", pady=1)
        self.gfx_osc_recv_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_osc3, text="OSC Receiver (MeowFace/VTube Studio, N key)", variable=self.gfx_osc_recv_var).pack(side="left", padx=(0, 15))
        ttk.Label(r_osc3, text="Port:").pack(side="left")
        self.gfx_osc_recv_port_var = tk.IntVar(value=11111)
        ttk.Entry(r_osc3, textvariable=self.gfx_osc_recv_port_var, width=6).pack(side="left", padx=(5, 0))

        # ── Window Crop ──
        f_crop = ttk.LabelFrame(gfx_inner, text="  Window Crop  ", padding=6)
        f_crop.pack(fill="x", pady=3)
        r_cr1 = ttk.Frame(f_crop); r_cr1.pack(fill="x", pady=1)
        self.gfx_crop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_cr1, text="Enable Crop (Shift+C)", variable=self.gfx_crop_var).pack(side="left", padx=(0, 15))
        r_cr2 = ttk.Frame(f_crop); r_cr2.pack(fill="x", pady=1)
        ttk.Label(r_cr2, text="Margin:", width=12, anchor="w").pack(side="left")
        self.gfx_crop_margin_var = tk.DoubleVar(value=0.0)
        ttk.Scale(r_cr2, from_=0, to=0.5, orient="horizontal",
                  variable=self.gfx_crop_margin_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r_cr2, text="Border:").pack(side="left")
        self.gfx_crop_border_var = tk.DoubleVar(value=0.02)
        ttk.Scale(r_cr2, from_=0, to=0.1, orient="horizontal",
                  variable=self.gfx_crop_border_var, length=100).pack(side="left", padx=(5, 0))
        r_cr3 = ttk.Frame(f_crop); r_cr3.pack(fill="x", pady=1)
        ttk.Label(r_cr3, text="Square Rate:", width=12, anchor="w").pack(side="left")
        self.gfx_crop_square_var = tk.DoubleVar(value=0.0)
        ttk.Scale(r_cr3, from_=0, to=1, orient="horizontal",
                  variable=self.gfx_crop_square_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r_cr3, text="Border RGB:").pack(side="left")
        self.gfx_crop_color_var = tk.StringVar(value="1.0,1.0,1.0")
        ttk.Entry(r_cr3, textvariable=self.gfx_crop_color_var, width=14).pack(side="left", padx=(5, 0))

        # ── Breast Jiggle ──
        f_breast = ttk.LabelFrame(gfx_inner, text="  Breast Jiggle  ", padding=6)
        f_breast.pack(fill="x", pady=3)
        r_br1 = ttk.Frame(f_breast); r_br1.pack(fill="x", pady=1)
        ttk.Label(r_br1, text="Stiffness:", width=12, anchor="w").pack(side="left")
        self.gfx_breast_stiff_var = tk.DoubleVar(value=1.5)
        ttk.Scale(r_br1, from_=0.1, to=5.0, orient="horizontal",
                  variable=self.gfx_breast_stiff_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r_br1, text="Gravity:").pack(side="left")
        self.gfx_breast_grav_var = tk.DoubleVar(value=0.3)
        ttk.Scale(r_br1, from_=0, to=1.0, orient="horizontal",
                  variable=self.gfx_breast_grav_var, length=100).pack(side="left", padx=(5, 0))
        r_br2 = ttk.Frame(f_breast); r_br2.pack(fill="x", pady=1)
        ttk.Label(r_br2, text="Drag:", width=12, anchor="w").pack(side="left")
        self.gfx_breast_drag_var = tk.DoubleVar(value=0.45)
        ttk.Scale(r_br2, from_=0.1, to=1.0, orient="horizontal",
                  variable=self.gfx_breast_drag_var, length=100).pack(side="left", padx=(0, 10))
        ttk.Label(r_br2, text="Bounce:").pack(side="left")
        self.gfx_breast_bounce_var = tk.DoubleVar(value=0.3)
        ttk.Scale(r_br2, from_=0, to=1.0, orient="horizontal",
                  variable=self.gfx_breast_bounce_var, length=100).pack(side="left", padx=(5, 0))
        r_br3 = ttk.Frame(f_breast); r_br3.pack(fill="x", pady=1)
        ttk.Label(r_br3, text="Scale:", width=12, anchor="w").pack(side="left")
        self.gfx_breast_scale_var = tk.DoubleVar(value=1.0)
        ttk.Scale(r_br3, from_=0.2, to=2.0, orient="horizontal",
                  variable=self.gfx_breast_scale_var, length=100).pack(side="left", padx=(0, 10))

        # ── Effects ──
        f_fx = ttk.LabelFrame(gfx_inner, text="  Effects  ", padding=6)
        f_fx.pack(fill="x", pady=3)
        r_fx1 = ttk.Frame(f_fx); r_fx1.pack(fill="x", pady=1)
        self.gfx_procedural_idle_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1, text="Procedural Face Idle", variable=self.gfx_procedural_idle_var).pack(side="left", padx=(0, 15))
        self.gfx_voice_triggers_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1, text="Voice Expression Triggers", variable=self.gfx_voice_triggers_var).pack(side="left", padx=(0, 15))
        self.gfx_interactive_bg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1, text="Interactive BG", variable=self.gfx_interactive_bg_var).pack(side="left", padx=(0, 15))
        self.gfx_breathing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1, text="Breathing", variable=self.gfx_breathing_var).pack(side="left", padx=(0, 15))
        r_fx1b = ttk.Frame(f_fx); r_fx1b.pack(fill="x", pady=1)
        self.gfx_head_ik_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1b, text="Head IK", variable=self.gfx_head_ik_var).pack(side="left", padx=(0, 15))
        self.gfx_head_stab_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1b, text="Head Stabilize", variable=self.gfx_head_stab_var).pack(side="left", padx=(0, 15))
        self.gfx_leg_ik_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1b, text="Leg IK", variable=self.gfx_leg_ik_var).pack(side="left", padx=(0, 15))
        self.gfx_hand_ik_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1b, text="Hand IK", variable=self.gfx_hand_ik_var).pack(side="left", padx=(0, 15))
        self.gfx_idle_anim_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx1b, text="Idle Animation", variable=self.gfx_idle_anim_var).pack(side="left", padx=(0, 15))
        r_fx2 = ttk.Frame(f_fx); r_fx2.pack(fill="x", pady=1)
        self.gfx_saccades_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx2, text="Saccades", variable=self.gfx_saccades_var).pack(side="left", padx=(0, 15))
        self.gfx_eye_lookat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx2, text="Eye LookAt", variable=self.gfx_eye_lookat_var).pack(side="left", padx=(0, 15))
        self.gfx_auto_blink_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx2, text="Auto Blink", variable=self.gfx_auto_blink_var).pack(side="left", padx=(0, 15))
        self.gfx_desktop_motion_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx2, text="Desktop Motion", variable=self.gfx_desktop_motion_var).pack(side="left", padx=(0, 15))
        self.gfx_audio_reactivity_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx2, text="Audio Reactivity", variable=self.gfx_audio_reactivity_var).pack(side="left", padx=(0, 15))
        r_fx3 = ttk.Frame(f_fx); r_fx3.pack(fill="x", pady=1)
        self.gfx_springbone_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx3, text="SpringBone", variable=self.gfx_springbone_var).pack(side="left", padx=(0, 15))
        self.gfx_virtual_bone_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx3, text="Virtual Bone Physics", variable=self.gfx_virtual_bone_var).pack(side="left", padx=(0, 15))
        self.gfx_cloth_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx3, text="Cloth", variable=self.gfx_cloth_var).pack(side="left", padx=(0, 15))
        self.gfx_particles_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx3, text="Particles", variable=self.gfx_particles_var).pack(side="left", padx=(0, 15))
        self.gfx_gamepad_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx3, text="Gamepad (XInput)", variable=self.gfx_gamepad_var).pack(side="left", padx=(0, 15))
        self.gfx_spout_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx3, text="Spout Output", variable=self.gfx_spout_var).pack(side="left", padx=(0, 15))
        r_fx4 = ttk.Frame(f_fx); r_fx4.pack(fill="x", pady=1)
        self.gfx_bg_visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r_fx4, text="BG Visible", variable=self.gfx_bg_visible_var).pack(side="left", padx=(0, 15))
        self.gfx_acc_visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r_fx4, text="Acc Visible", variable=self.gfx_acc_visible_var).pack(side="left")
        r_fx5 = ttk.Frame(f_fx); r_fx5.pack(fill="x", pady=1)
        self.gfx_ndi_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx5, text="NDI Output", variable=self.gfx_ndi_var).pack(side="left", padx=(0, 15))
        self.gfx_websocket_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx5, text="WebSocket", variable=self.gfx_websocket_var).pack(side="left", padx=(0, 15))
        self.gfx_gesture_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx5, text="Gesture Map", variable=self.gfx_gesture_var).pack(side="left", padx=(0, 15))
        r_fx6 = ttk.Frame(f_fx); r_fx6.pack(fill="x", pady=1)
        self.gfx_stretch_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx6, text="Stretch Bones", variable=self.gfx_stretch_var).pack(side="left", padx=(0, 15))
        self.gfx_pendulum_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx6, text="Pendulum Chains", variable=self.gfx_pendulum_var).pack(side="left", padx=(0, 15))
        self.gfx_liquid_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx6, text="Liquid Physics", variable=self.gfx_liquid_var).pack(side="left", padx=(0, 15))
        self.gfx_audiolink_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx6, text="AudioLink", variable=self.gfx_audiolink_var).pack(side="left", padx=(0, 15))
        self.gfx_plugin_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx6, text="Plugins", variable=self.gfx_plugin_var).pack(side="left")
        r_fx7 = ttk.Frame(f_fx); r_fx7.pack(fill="x", pady=1)
        self.gfx_throwable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx7, text="Throwable Items", variable=self.gfx_throwable_var).pack(side="left", padx=(0, 15))
        self.gfx_headpat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx7, text="Head Pats", variable=self.gfx_headpat_var).pack(side="left", padx=(0, 15))
        self.gfx_emotes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx7, text="Emotes", variable=self.gfx_emotes_var).pack(side="left", padx=(0, 15))
        self.gfx_ragdoll_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx7, text="Ragdoll", variable=self.gfx_ragdoll_var).pack(side="left", padx=(0, 15))
        self.gfx_rooms_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_fx7, text="Rooms", variable=self.gfx_rooms_var).pack(side="left")
        r_fx8 = ttk.Frame(f_fx); r_fx8.pack(fill="x", pady=1)
        ttk.Label(r_fx8, text="Emotes Dir:", width=12, anchor="w").pack(side="left")
        self.gfx_emotes_dir_var = tk.StringVar(value="")
        ttk.Entry(r_fx8, textvariable=self.gfx_emotes_dir_var, width=40).pack(side="left", padx=(0, 5))
        ttk.Label(r_fx8, text="Rooms File:", width=12, anchor="w").pack(side="left")
        self.gfx_rooms_file_var = tk.StringVar(value="")
        ttk.Entry(r_fx8, textvariable=self.gfx_rooms_file_var, width=40).pack(side="left")

        # ── Physically Based ──
        f_pbr = ttk.LabelFrame(gfx_inner, text="  PBR / Avanzado  ", padding=6)
        f_pbr.pack(fill="x", pady=3)
        r6a = ttk.Frame(f_pbr); r6a.pack(fill="x", pady=1)
        ttk.Label(r6a, text="Rim Power:", width=12, anchor="w").pack(side="left")
        self.gfx_rim_power_var = tk.DoubleVar(value=3.0)
        ttk.Scale(r6a, from_=0, to=10, orient="horizontal",
                  variable=self.gfx_rim_power_var, length=80).pack(side="left", padx=(0, 10))
        ttk.Label(r6a, text="Rim Int:").pack(side="left")
        self.gfx_rim_pbr_int_var = tk.DoubleVar(value=1.2)
        ttk.Scale(r6a, from_=0, to=3, orient="horizontal",
                  variable=self.gfx_rim_pbr_int_var, length=80).pack(side="left", padx=(5, 0))
        r6b = ttk.Frame(f_pbr); r6b.pack(fill="x", pady=1)
        ttk.Label(r6b, text="Rim Color R/G/B:", width=14, anchor="w").pack(side="left")
        self.gfx_rim_col_r_var = tk.StringVar(value="0.95")
        ttk.Entry(r6b, textvariable=self.gfx_rim_col_r_var, width=5).pack(side="left", padx=(0, 2))
        self.gfx_rim_col_g_var = tk.StringVar(value="0.9")
        ttk.Entry(r6b, textvariable=self.gfx_rim_col_g_var, width=5).pack(side="left", padx=2)
        self.gfx_rim_col_b_var = tk.StringVar(value="1.0")
        ttk.Entry(r6b, textvariable=self.gfx_rim_col_b_var, width=5).pack(side="left", padx=2)

        # Auto-save Gráficos settings to render_settings.json on any change
        self._gfx_save_timer = None
_gfx_bool_vars = [
            self.gfx_toon_var, self.gfx_edge_var, self.gfx_fxaa_var, self.gfx_bloom_var,
            self.gfx_look_mouse_var, self.gfx_idle_anim_var, self.gfx_leg_ik_var, self.gfx_head_ik_var,
            self.gfx_device_overlay_var, self.gfx_osc_var, self.gfx_osc_recv_var, self.gfx_crop_var,
            self.gfx_gamepad_var, self.gfx_spout_var, self.gfx_bg_visible_var,
            self.gfx_acc_visible_var, self.gfx_procedural_idle_var, self.gfx_voice_triggers_var,
            self.gfx_interactive_bg_var, self.gfx_ndi_var, self.gfx_websocket_var,
            self.gfx_gesture_var, self.gfx_stretch_var, self.gfx_pendulum_var,
            self.gfx_liquid_var, self.gfx_audiolink_var, self.gfx_plugin_var,
            self.gfx_throwable_var, self.gfx_headpat_var, self.gfx_emotes_var,
            self.gfx_ragdoll_var, self.gfx_rooms_var,
        ]
        _gfx_float_vars = [
            self.gfx_toon_cutoff_var, self.gfx_toon_smooth_var, self.gfx_shade_shift_var,
            self.gfx_rim_power_var, self.gfx_rim_pbr_int_var,
            self.gfx_outline_w_var, self.gfx_out_min_dist_var, self.gfx_out_max_dist_var,
            self.gfx_edge_norm_var, self.gfx_edge_depth_var,
            self.gfx_bloom_thresh_var, self.gfx_bloom_int_var, self.gfx_bloom_radius_var,
            self.gfx_ibl_int_var, self.gfx_hemi_int_var, self.gfx_fsr_sharp_var,
            self.gfx_crop_margin_var, self.gfx_crop_border_var, self.gfx_crop_square_var,
            self.gfx_breast_stiff_var, self.gfx_breast_grav_var, self.gfx_breast_drag_var,
            self.gfx_breast_bounce_var, self.gfx_breast_scale_var,
            self.gfx_osc_recv_port_var,
            self.gfx_osc_recv_port_var,
        _gfx_color_vars = [
            self.gfx_amb_r_var, self.gfx_amb_g_var, self.gfx_amb_b_var,
            self.gfx_rim_col_r_var, self.gfx_rim_col_g_var, self.gfx_rim_col_b_var,
            self.gfx_hemi_sky_r_var, self.gfx_hemi_sky_g_var, self.gfx_hemi_sky_b_var,
            self.gfx_hemi_gnd_r_var, self.gfx_hemi_gnd_g_var, self.gfx_hemi_gnd_b_var,
            self.gfx_outline_r_var, self.gfx_outline_g_var, self.gfx_outline_b_var,
            self.gfx_outline_a_var,
        ]
        for v in _gfx_bool_vars:
            v.trace_add("write", lambda *_: self._schedule_gfx_save())
        for v in _gfx_float_vars:
            v.trace_add("write", lambda *_: self._schedule_gfx_save())
        for v in _gfx_color_vars:
            v.trace_add("write", lambda *_: self._schedule_gfx_save())
        self.gfx_shade_color_var.trace_add("write", lambda *_: self._schedule_gfx_save())
        self.gfx_crop_color_var.trace_add("write", lambda *_: self._schedule_gfx_save())
        self.gfx_main_h_var.trace_add("write", lambda *_: self._schedule_gfx_save())
        self.gfx_main_p_var.trace_add("write", lambda *_: self._schedule_gfx_save())


        # ===== Tab: Hack Prohibidos =====
        tab_hack = ttk.Frame(notebook, padding=8)
        notebook.add(tab_hack, text="  Hack Prohibidos  ")

        hack_canvas = tk.Canvas(tab_hack, borderwidth=0, highlightthickness=0, bg="#1e1e1e")
        hack_scroll = ttk.Scrollbar(tab_hack, orient="vertical", command=hack_canvas.yview)
        hack_inner = ttk.Frame(hack_canvas)
        hack_inner.bind("<Configure>", lambda e: hack_canvas.configure(scrollregion=hack_canvas.bbox("all")))
        hack_canvas.create_window((0, 0), window=hack_inner, anchor="nw")
        hack_canvas.configure(yscrollcommand=hack_scroll.set)
        hack_canvas.pack(side="left", fill="both", expand=True)
        hack_scroll.pack(side="right", fill="y")

        self.hack_body_vars = {}

        def _hack_slider(parent, label, key, default=1.0, lo=0.3, hi=2.0):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label, width=18).pack(side="left")
            var = tk.DoubleVar(value=default)
            self.hack_body_vars[key] = var
            ttk.Scale(row, from_=lo, to=hi, orient="horizontal", variable=var, length=180).pack(side="left", padx=(5, 5))
            val_label = ttk.Label(row, text=f"{default:.2f}", width=6)
            val_label.pack(side="left")
            def _update(_name=None, _idx=None, _op=None, _vl=val_label, _v=var):
                _vl.config(text=f"{_v.get():.2f}")
                self._schedule_gfx_save()
            var.trace_add("write", lambda *_: _update())
            return var

        # Overall
        f_ov = ttk.LabelFrame(hack_inner, text="  Escala General  ", padding=6)
        f_ov.pack(fill="x", pady=3)
        _hack_slider(f_ov, "Escala General", "body_overall_scale", 1.0, 0.3, 2.0)

        # Arms
        f_arm = ttk.LabelFrame(hack_inner, text="  Brazos  ", padding=6)
        f_arm.pack(fill="x", pady=3)
        _hack_slider(f_arm, "Largo", "body_arm_length", 1.0, 0.5, 2.0)
        _hack_slider(f_arm, "Grosor", "body_arm_thickness", 1.0, 0.3, 2.5)

        # Legs
        f_leg = ttk.LabelFrame(hack_inner, text="  Piernas  ", padding=6)
        f_leg.pack(fill="x", pady=3)
        _hack_slider(f_leg, "Largo", "body_leg_length", 1.0, 0.5, 2.0)
        _hack_slider(f_leg, "Grosor", "body_leg_thickness", 1.0, 0.3, 2.5)

        # Torso
        f_torso = ttk.LabelFrame(hack_inner, text="  Torso / Pecho  ", padding=6)
        f_torso.pack(fill="x", pady=3)
        _hack_slider(f_torso, "Pecho", "body_chest", 1.0, 0.5, 2.0)
        _hack_slider(f_torso, "Ancho Cadera", "body_hip_width", 1.0, 0.5, 2.0)
        _hack_slider(f_torso, "Largo Torso", "body_torso_length", 1.0, 0.5, 2.0)

        # Head
        f_head = ttk.LabelFrame(hack_inner, text="  Cabeza  ", padding=6)
        f_head.pack(fill="x", pady=3)
        _hack_slider(f_head, "Tamano Cabeza", "body_head_size", 1.0, 0.5, 2.0)

        # Reset button
        ttk.Button(hack_inner, text="Restablecer Todo", command=lambda: self._reset_hack_body()).pack(pady=8)

        # ===== Tab: Controles =====
        tab_keys = ttk.Frame(notebook, padding=8)
        notebook.add(tab_keys, text="  Controles  ")

        controls = [
            ("", ""),
            ("CAMARA", ""),
            ("Click izq + drag", "Orbitar"),
            ("Click der + drag", "Mover modelo"),
            ("Scroll", "Zoom in/out"),
            ("Flechas", "Orbitar (teclado)"),
            ("+/-", "Zoom"),
            ("W/A/S/D", "Mover modelo"),
            ("R", "Reset camara"),
            ("", ""),
            ("EFECTOS", ""),
            ("G", "Chroma key on/off"),
            ("E", "Edge detect on/off"),
            ("", ""),
            ("LUZ", ""),
            ("Z / X", "Luz izq / der"),
            ("C / V", "Luz arriba / abajo"),
            ("B", "Intensidad luz"),
            ("", ""),
            ("BREAST JIGGLE", ""),
            ("", "Configurar en Graficos > PBR/Avanzado"),
            ("", ""),
            ("RENDER", ""),
            ("F", "FPS: 15 / 30 / 60"),
            ("Y", "FSR: Off / UP / Perf / Bal / Qual"),
            ("", ""),
            ("OSC OUTPUT / SPOUT", ""),
            ("O", "OSC output on/off"),
            ("Shift+O", "Spout output on/off"),
            ("", ""),
            ("MOTION", ""),
            ("I", "Cargar archivo de movimiento (BVH/JSON/VMC/VMD)"),
            ("U", "Play / Pausar movimiento"),
            ("J", "Detener movimiento"),
            ("K", "Velocidad: 0.25x / 0.5x / 1x / 1.5x / 2x"),
            ("Shift+Flechas", "Seek motion (-2s / +2s)"),
            ("Ctrl+Flechas", "Seek frame-accurate (±1 frame)"),
            ("M", "Modo baile (procedural)"),
            ("Shift+M", "Detener baile"),
            ("", ""),
            ("LIP SYNC", ""),
            ("[", "Micrófono Lip Sync on/off"),
            ("P", "Cargar audio (.wav/.mp3) + Lip Sync"),
            ("Shift+P", "Detener audio"),
            ("", ""),
            ("WEBCAM", ""),
            ("N", "Face tracking webcam on/off"),
            ("", ""),
            ("OTROS", ""),
            ("H", "Mostrar ayuda en consola"),
            ("", ""),
            ("FONDO / ACCESORIOS", ""),
            ("F1", "Cargar imagen de fondo"),
            ("F2", "Activar/desactivar fondo"),
            ("F3", "Agregar accesorio PNG"),
            ("F4", "Mostrar/ocultar accesorios"),
            ("", ""),
            ("SCREENSHOT", ""),
            ("F12", "Guardar screenshot PNG"),
            ("", ""),
            ("MODELO", ""),
            ("F5", "Recargar modelo actual"),
            ("Shift+F5", "Cambiar modelo (dialogo)"),
            ("", ""),
            ("EXPRESIONES", ""),
            ("0", "Reset expresiones"),
            ("1", "Blink"),
            ("2", "Angry"),
            ("3", "Joy"),
            ("4", "Sorrow"),
            ("5", "Fun"),
            ("6", "Aa"),
            ("7", "Ee"),
            ("8", "Oh"),
            ("9", "Ou"),
        ]
        for key, desc in controls:
            if not key and not desc:
                ttk.Separator(tab_keys, orient="horizontal").pack(fill="x", pady=2)
                continue
            if not desc:
                ttk.Label(tab_keys, text=key, font=("Segoe UI", 9, "bold"),
                          anchor="w").pack(fill="x", pady=(4, 0))
                continue
            row = ttk.Frame(tab_keys)
            row.pack(fill="x", padx=2, pady=1)
            ttk.Label(row, text=key, width=16, anchor="w",
                      font=("Consolas", 9, "bold")).pack(side="left")
            ttk.Label(row, text=desc, anchor="w").pack(side="left", padx=(5, 0))

        # Expression hotkey configuration
        ttk.Separator(tab_keys, orient="horizontal").pack(fill="x", pady=2)
        ttk.Label(tab_keys, text="CONFIGURAR EXPRESIONES",
                  font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(4, 0))
        ttk.Label(tab_keys, text="Asigna un preset VRM a cada tecla (0 = reset):",
                  anchor="w").pack(fill="x")
        expr_frame = ttk.Frame(tab_keys)
        expr_frame.pack(fill="x", pady=4)
        self._expr_hotkey_vars = {}
        _VRM_EXPRESSIONS = ["", "blink", "blink_l", "blink_r",
                            "angry", "joy", "sorrow", "fun",
                            "aa", "ih", "ou", "ee", "oh",
                            "lookup", "lookdown", "lookleft", "lookright",
                            "happy", "sad", "relaxed", "surprised", "neutral"]
        _hotkeys = self._read_settings().get("expression_hotkeys", {})
        for i in range(10):
            kname = str(i)
            r = ttk.Frame(expr_frame)
            r.pack(fill="x", padx=2, pady=1)
            ttk.Label(r, text=f"Tecla {i}:", width=8, anchor="w",
                      font=("Consolas", 9, "bold")).pack(side="left")
            var = tk.StringVar(value=_hotkeys.get(kname, ""))
            cb = ttk.Combobox(r, textvariable=var, values=_VRM_EXPRESSIONS,
                              state="readonly", width=14)
            cb.pack(side="left", padx=(5, 0))
            cb.bind("<<ComboboxSelected>>",
                    lambda e, v=var, k=kname: self._on_expr_hotkey_change(k, v.get()))
            self._expr_hotkey_vars[kname] = var

        # ===== Tab: Tools =====
        tab_tools = ttk.Frame(notebook, padding=8)
        notebook.add(tab_tools, text="  Optimizar VRM  ")

        f_tools_model = ttk.Frame(tab_tools)
        f_tools_model.pack(fill="x", pady=3)
        ttk.Label(f_tools_model, text="Modelo:", width=10, anchor="w").pack(side="left")
        self.tools_model_var = tk.StringVar()
        ttk.Entry(f_tools_model, textvariable=self.tools_model_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f_tools_model, text="Examinar",
                   command=self._tools_browse).pack(side="right")

        f_tools_ops = ttk.LabelFrame(tab_tools, text="  Operaciones  ", padding=6)
        f_tools_ops.pack(fill="x", pady=4)
        self.tool_translate = tk.BooleanVar(value=True)
        self.tool_prune = tk.BooleanVar(value=False)
        self.tool_dedup = tk.BooleanVar(value=True)
        self.tool_opt = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_tools_ops, text="1. Traducir nombres japoneses → inglés",
                        variable=self.tool_translate).pack(anchor="w", pady=1)
        self.tool_strip = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_tools_ops, text="2. Eliminar huesos sin peso del skin (reduce joint texture)",
                        variable=self.tool_strip).pack(anchor="w", pady=1)
        ttk.Checkbutton(f_tools_ops, text="3. Podar morphs no referenciados (elimina ~50% del peso)",
                        variable=self.tool_prune).pack(anchor="w", pady=1)
        ttk.Checkbutton(f_tools_ops, text="4. Deduplicar vértices (reduce tamaño drásticamente)",
                        variable=self.tool_dedup).pack(anchor="w", pady=1)
        ttk.Checkbutton(f_tools_ops, text="5. Optimizar texturas (JPEG/PNG optimizado)",
                        variable=self.tool_opt).pack(anchor="w", pady=1)
        self.tool_cb = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_tools_ops, text="6. Copiar blend shapes desde otro modelo",
                        variable=self.tool_cb).pack(anchor="w", pady=1)
        self.tool_vrm1 = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_tools_ops, text="7. Convertir a VRM 1.0 (requiere Blender + VRM Add-on)",
                        variable=self.tool_vrm1).pack(anchor="w", pady=1)
        self.tool_virtual = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_tools_ops, text="8. Añadir morphs virtuales (blink/joy/aa/oh… si faltan)",
                        variable=self.tool_virtual).pack(anchor="w", pady=1)

        f_tools_cb = ttk.Frame(tab_tools)
        f_tools_cb.pack(fill="x", pady=2)
        ttk.Label(f_tools_cb, text="Blend shapes origen:", width=20, anchor="w").pack(side="left")
        self.tools_cb_var = tk.StringVar()
        ttk.Entry(f_tools_cb, textvariable=self.tools_cb_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f_tools_cb, text="Examinar",
                   command=self._tools_cb_browse).pack(side="right")

        f_tools_out = ttk.Frame(tab_tools)
        f_tools_out.pack(fill="x", pady=3)
        ttk.Label(f_tools_out, text="Salida:", width=10, anchor="w").pack(side="left")
        self.tools_out_var = tk.StringVar()
        ttk.Entry(f_tools_out, textvariable=self.tools_out_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        self.tools_out_var.set("_opt.glb")
        ttk.Label(f_tools_out, text="(sufijo)").pack(side="left", padx=(0, 5))
        ttk.Button(f_tools_out, text="Generar nombre",
                   command=self._tools_gen_name).pack(side="right")

        f_tools_run = ttk.Frame(tab_tools)
        f_tools_run.pack(fill="x", pady=4)
        self.tools_run_btn = ttk.Button(
            f_tools_run, text="Ejecutar", command=self._tools_run)
        self.tools_run_btn.pack(fill="x")

        f_tools_log = ttk.LabelFrame(tab_tools, text="  Log  ", padding=4)
        f_tools_log.pack(fill="both", expand=True, pady=2)
        self.tools_log = tk.Text(f_tools_log, height=14, wrap="word",
                                 font=("Consolas", 8), state="disabled")
        scroll = ttk.Scrollbar(f_tools_log, command=self.tools_log.yview)
        self.tools_log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tools_log.pack(fill="both", expand=True)

        # ===== Tab: Expressions (Blend Shapes) =====
        # Removed — uses built-in auto-blink in BlendShapeProxy

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 680) // 2
        y = (self.root.winfo_screenheight() - 720) // 2
        self.root.geometry(f"680x780+{x}+{y}")

        self._restore_settings()

    def run(self):
        self.root.mainloop()

    def _update_api_list(self):
        backend = self.backend_var.get()
        apis = BACKEND_APIS.get(backend, ["—"])
        self.api_combo["values"] = apis
        cur = self.api_var.get()
        if cur not in apis:
            self.api_var.set(apis[0])

    def _on_backend_change(self, event=None):
        self._update_api_list()

    def _list_presets(self):
        try:
            return [f[:-5] for f in os.listdir(self._presets_dir)
                    if f.endswith('.json')]
        except Exception:
            return []

    def _load_preset(self):
        name = self.preset_var.get().strip()
        if not name:
            return
        path = os.path.join(self._presets_dir, f"{name}.json")
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            return
        for key, val in data.items():
            attr = f"{key}_var"
            if hasattr(self, attr):
                var = getattr(self, attr)
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(val))
                elif isinstance(var, tk.DoubleVar):
                    var.set(float(val))
                elif isinstance(var, tk.IntVar):
                    var.set(int(val))
                elif isinstance(var, tk.StringVar):
                    var.set(str(val) if not isinstance(val, list) else ",".join(str(v) for v in val))

    def _save_preset(self):
        name = self.preset_var.get().strip()
        if not name:
            return
        config = self._build_config()
        path = os.path.join(self._presets_dir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        self.preset_combo["values"] = self._list_presets()

    def _delete_preset(self):
        name = self.preset_var.get().strip()
        if not name:
            return
        path = os.path.join(self._presets_dir, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            self.preset_combo["values"] = self._list_presets()

    def _read_settings(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "render_settings.json")
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _restore_settings(self):
        d = self._read_settings()
        if not d:
            return
        _map = {
            "chroma_key": (self.chroma_var, "bool"),
            "transparent_bg": (self.transparent_var, "bool"),
            "toon_mode": (self.gfx_toon_var, "bool"),
            "toon_cutoff": (self.gfx_toon_cutoff_var, "float"),
            "toon_smoothness": (self.gfx_toon_smooth_var, "float"),
            "toon_shade_shift": (self.gfx_shade_shift_var, "float"),
            "look_at_mouse": (self.gfx_look_mouse_var, "bool"),
            "idle_animation": (self.gfx_idle_anim_var, "bool"),
            "leg_ik": (self.gfx_leg_ik_var, "bool"),
            "head_ik": (self.gfx_head_ik_var, "bool"),
            "breathing_enabled": (self.gfx_breathing_var, "bool"),
            "head_stabilization_enabled": (self.gfx_head_stab_var, "bool"),
            "hand_ik_enabled": (self.gfx_hand_ik_var, "bool"),
            "desktop_motion_enabled": (self.gfx_desktop_motion_var, "bool"),
            "procedural_face_idle_enabled": (self.gfx_procedural_idle_var, "bool"),
            "voice_triggers_enabled": (self.gfx_voice_triggers_var, "bool"),
            "interactive_bg_enabled": (self.gfx_interactive_bg_var, "bool"),
            "auto_blink_enabled": (self.gfx_auto_blink_var, "bool"),
            "eye_lookat_enabled": (self.gfx_eye_lookat_var, "bool"),
            "saccades_enabled": (self.gfx_saccades_var, "bool"),
            "audio_reactivity_enabled": (self.gfx_audio_reactivity_var, "bool"),
            "virtual_bone_physics_enabled": (self.gfx_virtual_bone_var, "bool"),
            "springbone_enabled": (self.gfx_springbone_var, "bool"),
            "cloth_enabled": (self.gfx_cloth_var, "bool"),
            "particles_enabled": (self.gfx_particles_var, "bool"),
            "fxaa_enabled": (self.gfx_fxaa_var, "bool"),
            "bloom_enabled": (self.gfx_bloom_var, "bool"),
            "bloom_threshold": (self.gfx_bloom_thresh_var, "float"),
            "bloom_intensity": (self.gfx_bloom_int_var, "float"),
            "bloom_radius": (self.gfx_bloom_radius_var, "float"),
            "ibl_intensity": (self.gfx_ibl_int_var, "float"),
            "hemi_intensity": (self.gfx_hemi_int_var, "float"),
            "fsr_sharpness": (self.gfx_fsr_sharp_var, "float"),
            "outline_width": (self.gfx_outline_w_var, "float"),
            "outline_min_distance": (self.gfx_out_min_dist_var, "float"),
            "outline_max_distance": (self.gfx_out_max_dist_var, "float"),
            "edge_normal_strength": (self.gfx_edge_norm_var, "float"),
            "edge_depth_strength": (self.gfx_edge_depth_var, "float"),
            "osc_enabled": (self.gfx_osc_var, "bool"),
            "osc_port": (self.gfx_osc_port_var, "int"),
            "osc_rate": (self.gfx_osc_rate_var, "int"),
            "osc_receiver_enabled": (self.gfx_osc_recv_var, "bool"),
            "osc_receiver_port": (self.gfx_osc_recv_port_var, "int"),
            "osc_receiver_bind": (self.gfx_osc_addr_var, "str"),
            "device_overlay": (self.gfx_device_overlay_var, "bool"),
            "crop_enabled": (self.gfx_crop_var, "bool"),
            "crop_margin": (self.gfx_crop_margin_var, "float"),
            "crop_border_width": (self.gfx_crop_border_var, "float"),
            "crop_square_rate": (self.gfx_crop_square_var, "float"),
            "breast_stiffness": (self.gfx_breast_stiff_var, "float"),
            "breast_gravity": (self.gfx_breast_grav_var, "float"),
            "breast_drag": (self.gfx_breast_drag_var, "float"),
            "breast_bounce": (self.gfx_breast_bounce_var, "float"),
            "breast_scale": (self.gfx_breast_scale_var, "float"),
            "gamepad_enabled": (self.gfx_gamepad_var, "bool"),
            "spout_enabled": (self.gfx_spout_var, "bool"),
            "ndi_enabled": (self.gfx_ndi_var, "bool"),
            "websocket_enabled": (self.gfx_websocket_var, "bool"),
            "gesture_mapper_enabled": (self.gfx_gesture_var, "bool"),
            "stretch_bones_enabled": (self.gfx_stretch_var, "bool"),
            "pendulum_chains_enabled": (self.gfx_pendulum_var, "bool"),
            "liquid_enabled": (self.gfx_liquid_var, "bool"),
            "audiolink_enabled": (self.gfx_audiolink_var, "bool"),
            "plugin_enabled": (self.gfx_plugin_var, "bool"),
            "throwable_items_enabled": (self.gfx_throwable_var, "bool"),
            "head_pat_enabled": (self.gfx_headpat_var, "bool"),
            "emotes_enabled": (self.gfx_emotes_var, "bool"),
            "ragdoll_enabled": (self.gfx_ragdoll_var, "bool"),
            "rooms_enabled": (self.gfx_rooms_var, "bool"),
            "bg_visible": (self.gfx_bg_visible_var, "bool"),
            "accessories_visible": (self.gfx_acc_visible_var, "bool"),
            "webcam_tracking": (self.webcam_auto_var, "bool"),
            "webcam_smoothing": (self.webcam_smoothing_var, "float"),
            "webcam_eye_sensitivity": (self.webcam_eye_sens_var, "float"),
            "webcam_mouth_sensitivity": (self.webcam_mouth_sens_var, "float"),
            "webcam_head_sensitivity": (self.webcam_head_sens_var, "float"),
            "webcam_mouth_gain": (self.webcam_mouth_gain_var, "float"),
            "webcam_pitch_offset": (self.webcam_pitch_var, "float"),
            "webcam_yaw_offset": (self.webcam_yaw_var, "float"),
            "mic_lipsync": (self.mic_lipsync_var, "bool"),
            "emotes_dir": (self.gfx_emotes_dir_var, "str"),
            "rooms_file": (self.gfx_rooms_file_var, "str"),
        }
        for key, (var, typ) in _map.items():
            if key in d:
                val = d[key]
                if typ == "bool":
                    var.set(bool(val))
                elif typ == "float":
                    var.set(float(val))
                elif typ == "int":
                    var.set(int(val))
                elif typ == "str":
                    var.set(str(val))
        # Body proportions
        for key, var in self.hack_body_vars.items():
            if key in d:
                var.set(float(d[key]))

    def _write_settings(self, settings):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "render_settings.json")
        with open(path, "w") as f:
            json.dump(settings, f, indent=2)

    def _reset_hack_body(self):
        for key, var in self.hack_body_vars.items():
            var.set(1.0)
        self._schedule_gfx_save()

    def _schedule_gfx_save(self):
        if hasattr(self, '_gfx_save_timer') and self._gfx_save_timer:
            self._gfx_save_timer.cancel()
        self._gfx_save_timer = threading.Timer(0.2, self._save_gfx_to_settings)
        self._gfx_save_timer.daemon = True
        self._gfx_save_timer.start()

    def _save_gfx_to_settings(self):
        self._gfx_save_timer = None
        settings = self._read_settings()
        # Float settings
        for key, var in [
            ("toon_cutoff", self.gfx_toon_cutoff_var),
            ("toon_smoothness", self.gfx_toon_smooth_var),
            ("toon_shade_shift", self.gfx_shade_shift_var),
            ("rim_power", self.gfx_rim_power_var),
            ("rim_intensity", self.gfx_rim_pbr_int_var),
            ("outline_width", self.gfx_outline_w_var),
            ("outline_min_distance", self.gfx_out_min_dist_var),
            ("outline_max_distance", self.gfx_out_max_dist_var),
            ("edge_normal_strength", self.gfx_edge_norm_var),
            ("edge_depth_strength", self.gfx_edge_depth_var),
            ("bloom_threshold", self.gfx_bloom_thresh_var),
            ("bloom_intensity", self.gfx_bloom_int_var),
            ("bloom_radius", self.gfx_bloom_radius_var),
            ("ibl_intensity", self.gfx_ibl_int_var),
            ("hemi_intensity", self.gfx_hemi_int_var),
            ("fsr_sharpness", self.gfx_fsr_sharp_var),
            ("crop_margin", self.gfx_crop_margin_var),
            ("crop_border_width", self.gfx_crop_border_var),
            ("crop_square_rate", self.gfx_crop_square_var),
            ("breast_stiffness", self.gfx_breast_stiff_var),
            ("breast_gravity", self.gfx_breast_grav_var),
            ("breast_drag", self.gfx_breast_drag_var),
            ("breast_bounce", self.gfx_breast_bounce_var),
            ("breast_scale", self.gfx_breast_scale_var),
        ]:
            settings[key] = float(var.get())
        # Bool settings
        for key, var in [
            ("toon_mode", self.gfx_toon_var),
            ("edge_detect_enabled", self.gfx_edge_var),
            ("fxaa_enabled", self.gfx_fxaa_var),
            ("bloom_enabled", self.gfx_bloom_var),
            ("look_at_mouse", self.gfx_look_mouse_var),
            ("idle_animation", self.gfx_idle_anim_var),
            ("leg_ik", self.gfx_leg_ik_var),
            ("head_ik", self.gfx_head_ik_var),
            ("device_overlay", self.gfx_device_overlay_var),
            ("osc_enabled", self.gfx_osc_var),
            ("osc_receiver_enabled", self.gfx_osc_recv_var),
            ("crop_enabled", self.gfx_crop_var),
            ("gamepad_enabled", self.gfx_gamepad_var),
            ("spout_enabled", self.gfx_spout_var),
            ("bg_visible", self.gfx_bg_visible_var),
            ("accessories_visible", self.gfx_acc_visible_var),
            ("procedural_face_idle_enabled", self.gfx_procedural_idle_var),
            ("voice_triggers_enabled", self.gfx_voice_triggers_var),
            ("interactive_bg_enabled", self.gfx_interactive_bg_var),
            ("breathing_enabled", self.gfx_breathing_var),
            ("head_ik", self.gfx_head_ik_var),
            ("head_stabilization_enabled", self.gfx_head_stab_var),
            ("leg_ik", self.gfx_leg_ik_var),
            ("hand_ik_enabled", self.gfx_hand_ik_var),
            ("idle_animation", self.gfx_idle_anim_var),
            ("saccades_enabled", self.gfx_saccades_var),
            ("eye_lookat_enabled", self.gfx_eye_lookat_var),
            ("auto_blink_enabled", self.gfx_auto_blink_var),
            ("desktop_motion_enabled", self.gfx_desktop_motion_var),
            ("audio_reactivity_enabled", self.gfx_audio_reactivity_var),
            ("virtual_bone_physics_enabled", self.gfx_virtual_bone_var),
            ("springbone_enabled", self.gfx_springbone_var),
            ("cloth_enabled", self.gfx_cloth_var),
            ("particles_enabled", self.gfx_particles_var),
            ("ndi_enabled", self.gfx_ndi_var),
            ("websocket_enabled", self.gfx_websocket_var),
            ("gesture_mapper_enabled", self.gfx_gesture_var),
            ("stretch_bones_enabled", self.gfx_stretch_var),
            ("pendulum_chains_enabled", self.gfx_pendulum_var),
            ("liquid_enabled", self.gfx_liquid_var),
            ("audiolink_enabled", self.gfx_audiolink_var),
            ("plugin_enabled", self.gfx_plugin_var),
            ("throwable_items_enabled", self.gfx_throwable_var),
            ("head_pat_enabled", self.gfx_headpat_var),
            ("emotes_enabled", self.gfx_emotes_var),
            ("ragdoll_enabled", self.gfx_ragdoll_var),
            ("rooms_enabled", self.gfx_rooms_var),
        ]:
            settings[key] = bool(var.get())
        emotes_dir = self.gfx_emotes_dir_var.get().strip()
        if emotes_dir:
            settings["emotes_dir"] = emotes_dir
        rooms_file = self.gfx_rooms_file_var.get().strip()
        if rooms_file:
            settings["rooms_file"] = rooms_file
        # RGB settings (separate StringVars)
        settings["ambient_color"] = [
            float(self.gfx_amb_r_var.get()), float(self.gfx_amb_g_var.get()),
            float(self.gfx_amb_b_var.get()), 1.0]
        settings["rim_color"] = [
            float(self.gfx_rim_col_r_var.get()), float(self.gfx_rim_col_g_var.get()),
            float(self.gfx_rim_col_b_var.get())]
        settings["hemi_sky_color"] = [
            float(self.gfx_hemi_sky_r_var.get()), float(self.gfx_hemi_sky_g_var.get()),
            float(self.gfx_hemi_sky_b_var.get())]
        settings["hemi_ground_color"] = [
            float(self.gfx_hemi_gnd_r_var.get()), float(self.gfx_hemi_gnd_g_var.get()),
            float(self.gfx_hemi_gnd_b_var.get())]
        settings["outline_color"] = [
            float(self.gfx_outline_r_var.get()), float(self.gfx_outline_g_var.get()),
            float(self.gfx_outline_b_var.get()), float(self.gfx_outline_a_var.get())]
        # Color string settings
        settings["toon_shade_color"] = self._parse_color(
            self.gfx_shade_color_var.get(), [0.55, 0.42, 0.48])
        settings["crop_border_color"] = self._parse_color(
            self.gfx_crop_color_var.get(), [1.0, 1.0, 1.0])
        # Body proportions (Hack Prohibidos)
        for key, var in self.hack_body_vars.items():
            settings[key] = float(var.get())
        # Main light HPR
        settings["main_light"] = {
            "hpr": [float(self.gfx_main_h_var.get()), float(self.gfx_main_p_var.get()), 0.0],
            "color": settings.get("main_light", {}).get("color", [0.7, 0.7, 0.7, 1.0])
        }
        self._write_settings(settings)

    def _on_expr_hotkey_change(self, key_name, preset):
        settings = self._read_settings()
        hotkeys = settings.get("expression_hotkeys", {})
        if preset:
            hotkeys[key_name] = preset
        else:
            hotkeys.pop(key_name, None)
        settings["expression_hotkeys"] = hotkeys
        self._write_settings(settings)

    def _save_config_dialog(self):
        path = filedialog.asksaveasfilename(
            title="Guardar configuracion",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="render_config.json")
        if not path:
            return
        config = self._build_config()
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            self.status_var.set(f"Config guardada: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    def _parse_color(self, s, default):
        parts = [x.strip() for x in s.split(",")]
        try:
            return [float(x) for x in parts]
        except Exception:
            return default

    def _build_config(self):
        config = {
            "model_path": self.model_var.get().strip(),
            "window_width": int(self.res_w.get()),
            "window_height": int(self.res_h.get()),
            "fps_limit": int(self.fps_var.get()),
            "chroma_key": self.chroma_var.get(),
            "transparent_bg": self.transparent_var.get(),
            "render_mode": self.render_mode_var.get(),
            "toon_mode": self.gfx_toon_var.get(),
            "toon_cutoff": self.gfx_toon_cutoff_var.get(),
            "toon_smoothness": self.gfx_toon_smooth_var.get(),
            "toon_shade_shift": self.gfx_shade_shift_var.get(),
            "toon_shade_color": self._parse_color(self.gfx_shade_color_var.get(), [0.55, 0.42, 0.48]),
            "ambient_color": [float(self.gfx_amb_r_var.get()), float(self.gfx_amb_g_var.get()), float(self.gfx_amb_b_var.get()), 1.0],
            "main_light": {"hpr": [float(self.gfx_main_h_var.get()), float(self.gfx_main_p_var.get()), 0.0], "color": [0.7, 0.7, 0.7, 1.0]},
            "rim_power": self.gfx_rim_power_var.get(),
            "rim_intensity": self.gfx_rim_pbr_int_var.get(),
            "rim_color": self._parse_color(f"{self.gfx_rim_col_r_var.get()},{self.gfx_rim_col_g_var.get()},{self.gfx_rim_col_b_var.get()}", [0.95, 0.9, 1.0]),
            "outline_color": [float(self.gfx_outline_r_var.get()), float(self.gfx_outline_g_var.get()), float(self.gfx_outline_b_var.get()), float(self.gfx_outline_a_var.get())],
            "outline_width": self.gfx_outline_w_var.get(),
            "outline_min_distance": self.gfx_out_min_dist_var.get(),
            "outline_max_distance": self.gfx_out_max_dist_var.get(),
            "edge_normal_strength": self.gfx_edge_norm_var.get(),
            "edge_depth_strength": self.gfx_edge_depth_var.get(),
            "edge_detect_enabled": self.gfx_edge_var.get(),
            "fxaa_enabled": self.gfx_fxaa_var.get(),
            "bloom_enabled": self.gfx_bloom_var.get(),
            "device_overlay": self.gfx_device_overlay_var.get(),
            "osc_enabled": self.gfx_osc_var.get(),
            "osc_address": self.gfx_osc_addr_var.get().strip(),
            "osc_port": int(self.gfx_osc_port_var.get()),
            "osc_rate": int(self.gfx_osc_rate_var.get()),
            "osc_receiver_enabled": self.gfx_osc_recv_var.get(),
            "osc_receiver_port": int(self.gfx_osc_recv_port_var.get()),
            "osc_receiver_bind": self.gfx_osc_addr_var.get().strip(),
            "bloom_threshold": self.gfx_bloom_thresh_var.get(),
            "bloom_intensity": self.gfx_bloom_int_var.get(),
            "bloom_radius": self.gfx_bloom_radius_var.get(),
            "ibl_intensity": self.gfx_ibl_int_var.get(),
            "hemi_sky_color": [float(self.gfx_hemi_sky_r_var.get()), float(self.gfx_hemi_sky_g_var.get()), float(self.gfx_hemi_sky_b_var.get())],
            "hemi_ground_color": [float(self.gfx_hemi_gnd_r_var.get()), float(self.gfx_hemi_gnd_g_var.get()), float(self.gfx_hemi_gnd_b_var.get())],
            "hemi_intensity": self.gfx_hemi_int_var.get(),
            "look_at_mouse": self.gfx_look_mouse_var.get(),
            "idle_animation": self.gfx_idle_anim_var.get(),
            "leg_ik": self.gfx_leg_ik_var.get(),
            "head_ik": self.gfx_head_ik_var.get(),
            "fsr_mode": self.gfx_fsr_var.get(),
            "fsr_sharpness": self.gfx_fsr_sharp_var.get(),
            "output_resolution": self.gfx_out_res_var.get(),
            "crop_enabled": self.gfx_crop_var.get(),
            "crop_margin": self.gfx_crop_margin_var.get(),
            "crop_border_width": self.gfx_crop_border_var.get(),
            "crop_square_rate": self.gfx_crop_square_var.get(),
            "crop_border_color": self._parse_color(self.gfx_crop_color_var.get(), [1.0, 1.0, 1.0]),
            "breast_stiffness": self.gfx_breast_stiff_var.get(),
            "breast_gravity": self.gfx_breast_grav_var.get(),
            "breast_drag": self.gfx_breast_drag_var.get(),
            "breast_bounce": self.gfx_breast_bounce_var.get(),
            "breast_scale": self.gfx_breast_scale_var.get(),
            "gamepad_enabled": self.gfx_gamepad_var.get(),
            "spout_enabled": self.gfx_spout_var.get(),
            "bg_visible": self.gfx_bg_visible_var.get(),
            "accessories_visible": self.gfx_acc_visible_var.get(),
            "procedural_face_idle_enabled": self.gfx_procedural_idle_var.get(),
            "voice_triggers_enabled": self.gfx_voice_triggers_var.get(),
            "interactive_bg_enabled": self.gfx_interactive_bg_var.get(),
            "breathing_enabled": self.gfx_breathing_var.get(),
            "head_ik": self.gfx_head_ik_var.get(),
            "head_stabilization_enabled": self.gfx_head_stab_var.get(),
            "leg_ik": self.gfx_leg_ik_var.get(),
            "hand_ik_enabled": self.gfx_hand_ik_var.get(),
            "idle_animation": self.gfx_idle_anim_var.get(),
            "saccades_enabled": self.gfx_saccades_var.get(),
            "eye_lookat_enabled": self.gfx_eye_lookat_var.get(),
            "auto_blink_enabled": self.gfx_auto_blink_var.get(),
            "desktop_motion_enabled": self.gfx_desktop_motion_var.get(),
            "audio_reactivity_enabled": self.gfx_audio_reactivity_var.get(),
            "virtual_bone_physics_enabled": self.gfx_virtual_bone_var.get(),
            "springbone_enabled": self.gfx_springbone_var.get(),
            "cloth_enabled": self.gfx_cloth_var.get(),
            "particles_enabled": self.gfx_particles_var.get(),
            "throwable_items_enabled": self.gfx_throwable_var.get(),
            "head_pat_enabled": self.gfx_headpat_var.get(),
            "emotes_enabled": self.gfx_emotes_var.get(),
            "ragdoll_enabled": self.gfx_ragdoll_var.get(),
            "rooms_enabled": self.gfx_rooms_var.get(),
            "ndi_enabled": self.gfx_ndi_var.get(),
            "websocket_enabled": self.gfx_websocket_var.get(),
            "gesture_mapper_enabled": self.gfx_gesture_var.get(),
            "stretch_bones_enabled": self.gfx_stretch_var.get(),
            "pendulum_chains_enabled": self.gfx_pendulum_var.get(),
            "liquid_enabled": self.gfx_liquid_var.get(),
            "audiolink_enabled": self.gfx_audiolink_var.get(),
            "plugin_enabled": self.gfx_plugin_var.get(),
        }
        emotes_dir = self.gfx_emotes_dir_var.get().strip()
        if emotes_dir:
            config["emotes_dir"] = emotes_dir
        rooms_file = self.gfx_rooms_file_var.get().strip()
        if rooms_file:
            config["rooms_file"] = rooms_file
        api = self.api_var.get()
        if api and api != "—":
            config["render_api"] = api
        audio_path = self.audio_file_var.get().strip()
        if audio_path and os.path.exists(audio_path):
            config["audio_file_path"] = audio_path
        config["audio_auto_play"] = self.audio_auto_var.get()
        config["mic_lipsync"] = self.mic_lipsync_var.get()
        config["webcam_id"] = int(self.webcam_id_var.get())
        config["webcam_tracking"] = self.webcam_auto_var.get()
        config["webcam_smoothing"] = self.webcam_smoothing_var.get()
        config["webcam_eye_sensitivity"] = self.webcam_eye_sens_var.get()
        config["webcam_mouth_sensitivity"] = self.webcam_mouth_sens_var.get()
        config["webcam_mouth_gain"] = self.webcam_mouth_gain_var.get()
        config["webcam_head_sensitivity"] = self.webcam_head_sens_var.get()
        config["webcam_pitch_offset"] = self.webcam_pitch_var.get()
        config["webcam_yaw_offset"] = self.webcam_yaw_var.get()
        config["webcam_flip_x"] = self.webcam_flip_x_var.get()
        bg_path = self.bg_var.get().strip()
        if bg_path and os.path.exists(bg_path):
            config["bg_image"] = bg_path
        acc_path = self.acc_var.get().strip()
        if acc_path and os.path.exists(acc_path):
            config["accessory_items"] = [(acc_path, self.acc_bone_var.get().strip() or "Head")]
        tex_q = self._tex_size()
        if tex_q:
            config["max_texture_size"] = tex_q
        return config

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Seleccionar modelo",
            filetypes=[("Modelos 3D", "*.glb *.vrm *.pmx *.pmd"), ("Todos", "*.*")],
            initialdir=os.path.expandvars(r"%USERPROFILE%\Documents"))
        if path:
            self.model_var.set(path)
            self._save_recent(path)

    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="Seleccionar audio para lip sync",
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.ogg"), ("Todos", "*.*")])
        if path:
            self.audio_file_var.set(path)

    def _browse_bg(self):
        path = filedialog.askopenfilename(
            title="Seleccionar imagen de fondo",
            filetypes=[("Imagen", "*.png *.jpg *.jpeg *.bmp *.tga"), ("Todos", "*.*")])
        if path:
            self.bg_var.set(path)

    def _browse_acc(self):
        path = filedialog.askopenfilename(
            title="Seleccionar accesorio PNG",
            filetypes=[("PNG", "*.png"), ("Todos", "*.*")])
        if path:
            self.acc_var.set(path)

    def _base_dir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _recent_path(self):
        return os.path.join(self._base_dir(), ".recent_models.txt")

    def _save_recent(self, path):
        recent = self._get_recent_list()
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:5]
        try:
            with open(self._recent_path(), "w") as f:
                f.write("\n".join(recent))
        except Exception:
            pass

    def _get_recent_list(self):
        try:
            with open(self._recent_path()) as f:
                return [l.strip() for l in f if l.strip()]
        except Exception:
            return []

    def _load_recent(self, parent):
        recent = self._get_recent_list()
        if not recent:
            return
        f_recent = ttk.LabelFrame(parent, text="  Recientes  ", padding=5)
        f_recent.pack(fill="x", pady=5)
        for p in recent:
            name = os.path.basename(p)
            btn = ttk.Button(f_recent, text=name,
                             command=lambda path=p: self.model_var.set(path))
            btn.pack(fill="x", pady=1)

    def _launch(self):
        model = self.model_var.get().strip()
        if not model:
            messagebox.showerror("Error", "Selecciona un modelo")
            return
        if not os.path.exists(model):
            messagebox.showerror("Error", "Archivo no encontrado:\n" + model)
            return

        backend = self.backend_var.get()
        api = self.api_var.get()
        try:
            w = int(self.res_w.get())
            h = int(self.res_h.get())
        except ValueError:
            messagebox.showerror("Error", "Resolucion invalida")
            return

        self.status_var.set("Iniciando...")
        self.launch_btn.config(state="disabled")
        self._rendering = True

        threading.Thread(target=self._run_renderer,
                         args=(model, backend, api, w, h),
                         daemon=True).start()

        self.root.after(1000, self._check_done)

    def _tex_size(self):
        q = self.gfx_tex_qual_var.get()
        if q.startswith("Bajo"):
            return 128
        if q.startswith("Medio"):
            return 512
        return 0

    def _run_renderer(self, model, backend, api, w, h):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = self._build_config()
        config["max_texture_size"] = self._tex_size()
        cfg_tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False)
        json.dump(config, cfg_tmp)
        cfg_path = cfg_tmp.name
        cfg_tmp.close()
        launcher = os.path.join(base, "render", "launcher.py")
        cmd = [sys.executable, launcher,
               "--render", backend,
               "--config", cfg_path,
               "--window-width", str(w),
               "--window-height", str(h)]
        rm = self.render_mode_var.get()
        if rm != "cpu+gpu":
            cmd.extend(["--render-mode", rm])
        if api and api != "—":
            cmd.extend(["--api", api])
        cmd.append(model)
        try:
            subprocess.run(cmd, cwd=base)
        except Exception as e:
            self._error = str(e)
        finally:
            try:
                os.unlink(cfg_path)
            except Exception:
                pass
        self._done = True

    def _check_done(self):
        if getattr(self, '_done', False):
            self.status_var.set("Listo")
            self.launch_btn.config(state="normal")
            self._rendering = False
            err = getattr(self, '_error', None)
            if err:
                messagebox.showerror("Error", err)
        else:
            self.root.after(500, self._check_done)

    def _tools_browse(self):
        path = filedialog.askopenfilename(
            title="Seleccionar modelo",
            filetypes=[("Modelos 3D", "*.glb *.vrm"), ("Todos", "*.*")])
        if path:
            self.tools_model_var.set(path)
            self._tools_gen_name()

    def _tools_cb_browse(self):
        path = filedialog.askopenfilename(
            title="Seleccionar modelo con blend shapes",
            filetypes=[("Modelos 3D", "*.glb *.vrm"), ("Todos", "*.*")])
        if path:
            self.tools_cb_var.set(path)

    def _tools_gen_name(self):
        inp = self.tools_model_var.get().strip()
        if not inp:
            return
        base, ext = os.path.splitext(inp)
        suf = self.tools_out_var.get().strip() or "_opt"
        out = base + suf + ".glb"
        self.tools_out_path = out
        self._tools_log(f"Output: {out}\n")

    def _tools_log(self, msg):
        self.tools_log.configure(state="normal")
        self.tools_log.insert("end", msg)
        self.tools_log.see("end")
        self.tools_log.configure(state="disabled")

    def _tools_run(self):
        inp = self.tools_model_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "Selecciona un modelo válido")
            return
        do_cb = self.tool_cb.get()
        do_vrm1 = self.tool_vrm1.get()
        do_virtual = self.tool_virtual.get()
        if not any([self.tool_translate.get(), self.tool_strip.get(), self.tool_prune.get(), self.tool_dedup.get(), self.tool_opt.get(), do_cb, do_vrm1, do_virtual]):
            messagebox.showerror("Error", "Selecciona al menos una operación")
            return
        if do_cb:
            cb_src = self.tools_cb_var.get().strip()
            if not cb_src or not os.path.exists(cb_src):
                messagebox.showerror("Error", "Selecciona un modelo origen para copiar blend shapes")
                return

        self._tools_gen_name()
        out = getattr(self, 'tools_out_path', None)
        if not out:
            base, _ = os.path.splitext(inp)
            suf = self.tools_out_var.get().strip() or "_opt"
            ext = ".vrm" if (do_vrm1 or do_virtual) else ".glb"
            out = base + suf + ext
            self.tools_out_path = out

        self.tools_log.configure(state="normal")
        self.tools_log.delete("1.0", "end")
        self.tools_log.configure(state="disabled")
        self.tools_run_btn.config(state="disabled")
        self.status_var.set("Optimizando...")

        threading.Thread(target=self._tools_worker,
                         args=(inp, out), daemon=True).start()

    def _tools_worker(self, inp, out):
        import tempfile as tf

        def log(msg):
            self.root.after(0, self._tools_log, msg + "\n")

        do_tr = self.tool_translate.get()
        do_st = self.tool_strip.get()
        do_pr = self.tool_prune.get()
        do_dd = self.tool_dedup.get()
        do_ot = self.tool_opt.get()
        do_cb = self.tool_cb.get()
        cb_src = self.tools_cb_var.get().strip() if do_cb else None
        do_vrm1 = self.tool_vrm1.get()
        do_virtual = self.tool_virtual.get()

        # Find Blender for VRM 1.0 conversion
        blender_path = None
        if do_vrm1:
            candidates = [
                r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            ]
            for p in candidates:
                if os.path.exists(p):
                    blender_path = p
                    break
            if not blender_path:
                log("❌ Blender no encontrado. Instala Blender 5.0+ con VRM Add-on.")
                self.root.after(0, self._tools_cleanup)
                return

        steps = []
        # VRM 1.0 conversion must be FIRST (Blender import works best with original .vrm)
        if do_vrm1 and blender_path:
            convert_script = os.path.join(os.path.dirname(__file__), "tools", "vrm_convert_to_1.py")
            def vrm1_step(s, d, l):
                import subprocess as sp
                l("Ejecutando Blender headless...")
                result = sp.run([blender_path, "--background", "--python", convert_script, "--", s, d],
                               capture_output=True, text=True, timeout=300)
                for line in result.stdout.splitlines():
                    l("  " + line)
                if result.returncode != 0:
                    l("❌ Blender error:\n" + result.stderr)
                    raise RuntimeError(f"Blender exited with code {result.returncode}")
                l("✅ Conversión VRM 1.0 completada")
            steps.append(("Convert to VRM 1.0", vrm1_step))
        if do_tr:
            steps.append(("Translate JP→EN", lambda s, d, l: jptrans.translate(s, d, logfn=l)))
        if do_st:
            steps.append(("Strip zero-weight bones", lambda s, d, l: strip_bones.strip_zero_weight_bones(s, d, logfn=l)))
        if do_pr:
            steps.append(("Prune unreferenced morphs", lambda s, d, l: prune_morphs.prune_morphs(s, d, logfn=l)))
        if do_dd:
            steps.append(("Deduplicate vertices", lambda s, d, l: dedup.dedup_model(s, d, logfn=l)))
        if do_ot:
            steps.append(("Optimize textures", lambda s, d, l: optimize_tex.optimize(s, d, logfn=l)))
        if do_cb and cb_src:
            steps.append(("Copy blend shapes", lambda s, d, l, src=cb_src: copy_blendshapes.copy_blend_shapes(src, s, d, logfn=l)))
        if do_virtual:
            steps.append(("Add virtual morphs", lambda s, d, l: add_virtual_morphs.add_virtual_morphs(s, d, logfn=l)))

        n_steps = len(steps)
        tmpdir = tf.mkdtemp(prefix="karin_tools_")
        prev = inp
        try:
            for i, (label, func) in enumerate(steps):
                if i < n_steps - 1:
                    nxt = os.path.join(tmpdir, f"step_{i}.glb")
                else:
                    nxt = out
                log(f"\n=== Step {i+1}/{n_steps}: {label} ===")
                func(prev, nxt, log)
                prev = nxt
            log(f"\n✅ Done! Output: {out}")
        except Exception as e:
            log(f"\n❌ Error: {e}")
            import traceback
            log(traceback.format_exc())
        finally:
            import shutil
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
            self.root.after(0, self._tools_cleanup)

    def _tools_cleanup(self):
        self.tools_run_btn.config(state="normal")
        self.status_var.set("Listo")

    # Expression tab removed — uses built-in auto-blink in BlendShapeProxy


def main():
    app = LauncherUI()
    app.run()


if __name__ == "__main__":
    main()
