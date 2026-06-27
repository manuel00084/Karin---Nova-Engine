"""RendererConfig dataclass with JSON load/save."""
import json
import logging
from dataclasses import dataclass, field, asdict

_log = logging.getLogger("karin.config")


@dataclass
class LightConfig:
    color: list[float] = field(default_factory=lambda: [0.7, 0.7, 0.7, 1.0])
    hpr: list[float] = field(default_factory=lambda: [180.0, 20.0, 0.0])


@dataclass
class RendererConfig:
    model_path: str = ""
    window_title: str = "Karin - Nova Engine 3D"
    window_width: int = 960
    window_height: int = 720
    chroma_key: bool = False
    chroma_color: list[float] = field(default_factory=lambda: [0.0, 1.0, 0.0])
    bg_color: list[float] = field(default_factory=lambda: [0.2, 0.2, 0.2, 1.0])
    transparent_bg: bool = False
    ambient_color: list[float] = field(default_factory=lambda: [0.3, 0.3, 0.35, 1.0])
    main_light: LightConfig = field(default_factory=LightConfig)
    ws_port: int = 18081
    toon_mode: bool = False

    toon_cutoff: float = 0.3
    toon_smoothness: float = 0.08
    toon_shade_shift: float = 0.0
    toon_shade_color: list[float] = field(default_factory=lambda: [0.55, 0.42, 0.48])
    rim_power: float = 3.0
    rim_intensity: float = 1.2
    rim_color: list[float] = field(default_factory=lambda: [0.95, 0.9, 1.0])
    outline_color: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    outline_width: float = 0.005
    matcap_intensity: float = 0.5
    edge_normal_strength: float = 5.0
    edge_depth_strength: float = 5.0
    edge_width: float = 0.04
    edge_distance_fade: float = 0.5
    blink_strength: float = 1.0
    breath_amplitude: float = 0.008
    idle_animation: bool = False
    leg_ik: bool = False
    head_ik: bool = False
    breathing_enabled: bool = False
    head_stabilization_enabled: bool = False
    desktop_motion_enabled: bool = False
    procedural_face_idle_enabled: bool = False
    voice_triggers_enabled: bool = False
    interactive_bg_enabled: bool = False
    auto_blink_enabled: bool = False
    eye_lookat_enabled: bool = False
    virtual_bone_physics_enabled: bool = False
    springbone_enabled: bool = False
    cloth_enabled: bool = False
    particles_enabled: bool = False
    saccades_enabled: bool = False
    hand_ik_enabled: bool = False
    audio_reactivity_enabled: bool = False
    render_api: str = ""
    render_mode: str = "cpu+gpu"
    dance_path: str = "render/assets/low_cortisol.bvh"
    video_dance_path: str = ""
    max_texture_size: int = 0
    max_vertices: int = 0
    fps_limit: int = 60
    fsr_mode: str = "off"
    fsr_sharpness: float = 0.2
    output_resolution: str = "1080p"
    breast_stiffness: float = 1.5
    breast_gravity: float = 0.3
    breast_drag: float = 0.45
    breast_bounce: float = 0.3
    breast_scale: float = 1.0
    hemi_sky_color: list[float] = field(default_factory=lambda: [0.4, 0.5, 0.7])
    hemi_ground_color: list[float] = field(default_factory=lambda: [0.3, 0.25, 0.2])
    hemi_intensity: float = 0.5
    rim_light_dir: list[float] = field(default_factory=lambda: [0.0, -1.0, 0.5])
    rim_light_color: list[float] = field(default_factory=lambda: [0.8, 0.75, 1.0])
    rim_light_intensity: float = 0.6
    bg_image: str = ""
    accessory_items: list = field(default_factory=list)
    fxaa_enabled: bool = True
    bloom_enabled: bool = True
    bloom_threshold: float = 0.8
    bloom_intensity: float = 0.4
    bloom_radius: float = 4.0
    ibl_intensity: float = 0.5
    edge_detect_enabled: bool = False
    outline_min_distance: float = 1.0
    outline_max_distance: float = 12.0

    look_at_mouse: bool = True

    # Audio file lip sync
    audio_file_path: str = ""
    audio_auto_play: bool = False
    # Mic lip sync
    mic_lipsync: bool = False
    # Webcam face tracking
    webcam_id: int = 0
    webcam_tracking: bool = False
    webcam_smoothing: float = 8.0
    webcam_eye_sensitivity: float = 3.0
    webcam_mouth_sensitivity: float = 30.0
    webcam_head_sensitivity: float = 1.0
    webcam_mouth_gain: float = 1.5
    webcam_pitch_offset: float = 0.0
    webcam_yaw_offset: float = 0.0
    webcam_flip_x: bool = False

    # Window crop (circle/rounded square)
    crop_enabled: bool = False
    crop_margin: float = 0.0
    crop_border_width: float = 0.02
    crop_square_rate: float = 0.0
    crop_border_color: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])

    # Gamepad
    gamepad_enabled: bool = False

    # Spout output
    spout_enabled: bool = False

    # Effects toggles (must match UI checkboxes)
    bg_visible: bool = True
    accessories_visible: bool = True

    # Multi-light (additional lights beyond main_light)
    num_lights: int = 1
    light2_hpr: list[float] = field(default_factory=lambda: [45.0, -30.0, 0.0])
    light2_color: list[float] = field(default_factory=lambda: [0.5, 0.5, 0.5, 1.0])
    light2_intensity: float = 0.8
    light3_hpr: list[float] = field(default_factory=lambda: [135.0, -20.0, 0.0])
    light3_color: list[float] = field(default_factory=lambda: [0.4, 0.4, 0.5, 1.0])
    light3_intensity: float = 0.6
    light4_hpr: list[float] = field(default_factory=lambda: [-135.0, -45.0, 0.0])
    light4_color: list[float] = field(default_factory=lambda: [0.3, 0.3, 0.4, 1.0])
    light4_intensity: float = 0.5
    hud_enabled: bool = True
    device_overlay: bool = False

    # Expression hotkeys: key_name → expression_preset_name
    expression_hotkeys: dict[str, str] = field(default_factory=lambda: {
        "1": "blink", "2": "angry", "3": "joy", "4": "sorrow",
        "5": "fun", "6": "aa", "7": "ee", "8": "oh", "9": "ou",
        "0": "reset",
    })

    osc_enabled: bool = False
    osc_address: str = "127.0.0.1"
    osc_port: int = 9000
    osc_rate: int = 30
    osc_receiver_enabled: bool = False
    osc_receiver_port: int = 11111
    osc_receiver_bind: str = "0.0.0.0"

    # NDI output
    ndi_enabled: bool = False
    ndi_name: str = "Karin VTuber"

    # WebSocket receiver (Stream Deck / bots)
    websocket_enabled: bool = False
    websocket_host: str = "127.0.0.1"
    websocket_port: int = 8765

    # Gesture mapping
    gesture_mapper_enabled: bool = False

    # Stretch bones
    stretch_bones_enabled: bool = False

    # Pendulum chains
    pendulum_chains_enabled: bool = False

    # Liquid/slime physics
    liquid_enabled: bool = False

    # AudioLink (audio-reactive)
    audiolink_enabled: bool = False

    # Plugin system
    plugin_enabled: bool = False
    plugin_dirs: list = field(default_factory=lambda: ["render/plugins"])

    # Viewer interactions (VTuber Plus / TIFA style)
    throwable_items_enabled: bool = False
    head_pat_enabled: bool = False
    emotes_enabled: bool = False
    emotes_dir: str = ""
    ragdoll_enabled: bool = False
    ragdoll_duration: float = 3.0
    health_bar_enabled: bool = False
    health_max: float = 100.0
    health_regen: float = 0.5
    rooms_enabled: bool = False
    rooms_file: str = ""

    # Body proportions (Hack Prohibidos)
    body_arm_length: float = 1.0
    body_arm_thickness: float = 1.0
    body_leg_length: float = 1.0
    body_leg_thickness: float = 1.0
    body_chest: float = 1.0
    body_hip_width: float = 1.0
    body_head_size: float = 1.0
    body_torso_length: float = 1.0
    body_overall_scale: float = 1.0

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "RendererConfig":
        with open(path) as f:
            data = json.load(f)
        import dataclasses
        valid = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid}
        # Convert nested LightConfig dicts to proper dataclass instances
        for light_key in ("main_light",):
            if light_key in filtered and isinstance(filtered[light_key], dict):
                filtered[light_key] = LightConfig(**filtered[light_key])
        return cls(**filtered)
