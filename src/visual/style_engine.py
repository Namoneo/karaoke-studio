"""
Visual Style Engine
Maps mood → color palette, animation style, font selection, visual treatment.
Every song gets a unique visual identity.
"""

import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import List


@dataclass 
class VisualStyle:
    """Complete visual treatment for a song."""
    mood: str
    palette: List[str]          # hex colors
    bg_type: str                # background animation type
    bg_params: dict             # background animation parameters
    viz_type: str               # visualization type
    viz_params: dict            # visualization parameters
    font_primary: str           # main font path
    font_secondary: str         # secondary font path
    font_size_lyrics: int       # lyrics font size
    font_size_title: int        # title font size
    font_color: str             # lyrics font color
    font_outline: str           # outline color
    font_shadow: bool            # drop shadow
    transition_type: str        # lyric transition style
    particle_type: str          # particle effect
    particle_count: int         # number of particles
    gradient_direction: str     # gradient flow direction
    blur_amount: float          # background blur
    glow_intensity: float       # glow effect strength
    vignette: bool              # vignette overlay
    film_grain: float           # film grain amount (0.0 = none)
    light_leak: bool             # cinematic light leak
    letterbox: bool             # cinematic bars
    description: str            # human-readable description


# Font roles → ordered candidate files per platform (macOS, then common Linux
# locations, then Windows). resolve_font() returns the first that exists,
# falling back to matplotlib's bundled DejaVuSans so the pipeline runs on any
# platform even when none of the named fonts are installed.
_FONT_CANDIDATES = {
    "modern_sans": [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ],
    "rounded": [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/usr/share/fonts/truetype/quicksand/Quicksand-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
    ],
    "elegant_serif": [
        "/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
        "C:\\Windows\\Fonts\\georgia.ttf",
    ],
    "bold_sans": [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
    ],
    "clean_sans": [
        "/System/Library/Fonts/Avenir.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
    ],
    "mono": [
        "/System/Library/Fonts/Courier.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
    ],
}


def _matplotlib_fallback_font() -> str:
    """Path to DejaVuSans.ttf, which ships with matplotlib (a hard dependency),
    so it is available wherever the pipeline can run. Returns "" if not found."""
    try:
        import matplotlib
        p = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
        if p.exists():
            return str(p)
    except Exception:
        pass
    return ""


def resolve_font(role: str) -> str:
    """Resolve a logical font role to an existing font file on this platform.

    Tries the platform-specific candidates in order, then matplotlib's bundled
    DejaVuSans, and only as a last resort returns the first (macOS) candidate.
    """
    candidates = _FONT_CANDIDATES.get(role, _FONT_CANDIDATES["modern_sans"])
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    fallback = _matplotlib_fallback_font()
    return fallback or candidates[0]


def generate_style(mood: str, palette: list, energy: float, valence: float, bpm: float, seed: int = None) -> VisualStyle:
    """Generate a unique visual style for a song based on its mood and energy."""
    if seed is not None:
        random.seed(seed)
    
    # Background styles per mood
    bg_configs = {
        "dance": [
            {"type": "neon_grid", "params": {"speed": 2.0, "line_count": 40, "perspective": True}},
            {"type": "audio_reactive_bars", "params": {"speed": 1.5, "count": 64}},
            {"type": "neon_pulses", "params": {"speed": 2.0, "count": 12}},
            {"type": "gradient_waves", "params": {"speed": 2.5, "layers": 5}},
        ],
        "happy": [
            {"type": "floating_bubbles", "params": {"speed": 1.0, "count": 30}},
            {"type": "sunburst", "params": {"speed": 0.8, "rays": 12}},
            {"type": "gradient_flow", "params": {"speed": 1.2, "layers": 4}},
        ],
        "sad": [
            {"type": "rain_window", "params": {"speed": 0.5, "intensity": 0.8}},
            {"type": "slow_fog", "params": {"speed": 0.3, "density": 0.6}},
            {"type": "drifting_clouds", "params": {"speed": 0.4, "count": 8}},
            {"type": "falling_petals", "params": {"speed": 0.6, "count": 20}},
        ],
        "melancholic": [
            {"type": "slow_fog", "params": {"speed": 0.3, "density": 0.7}},
            {"type": "drifting_clouds", "params": {"speed": 0.3, "count": 10}},
            {"type": "ink_spread", "params": {"speed": 0.2}},
        ],
        "acoustic": [
            {"type": "floating_dust", "params": {"speed": 0.4, "count": 60}},
            {"type": "golden_particles", "params": {"speed": 0.3, "count": 40}},
            {"type": "warm_gradient", "params": {"speed": 0.5, "layers": 3}},
            {"type": "sunrise", "params": {"speed": 0.3}},
        ],
        "lofi": [
            {"type": "rain_window", "params": {"speed": 0.4, "intensity": 0.6}},
            {"type": "city_lights", "params": {"speed": 0.5, "count": 40}},
            {"type": "night_sky", "params": {"speed": 0.2, "stars": 200}},
            {"type": "bokeh", "params": {"speed": 0.3, "count": 25}},
        ],
        "romantic": [
            {"type": "floating_hearts", "params": {"speed": 0.5, "count": 15}},
            {"type": "warm_bokeh", "params": {"speed": 0.4, "count": 30}},
            {"type": "light_leaks", "params": {"speed": 0.3, "intensity": 0.5}},
            {"type": "golden_particles", "params": {"speed": 0.4, "count": 50}},
            {"type": "sunset_gradient", "params": {"speed": 0.3, "layers": 4}},
        ],
        "epic": [
            {"type": "space_nebula", "params": {"speed": 0.5, "stars": 300}},
            {"type": "mountain_silhouette", "params": {"speed": 0.3, "layers": 5}},
            {"type": "aurora", "params": {"speed": 0.6, "intensity": 0.8}},
            {"type": "cosmic_dust", "params": {"speed": 0.4, "count": 200}},
        ],
        "ambient": [
            {"type": "slow_gradient", "params": {"speed": 0.2, "layers": 3}},
            {"type": "floating_dust", "params": {"speed": 0.2, "count": 80}},
            {"type": "aurora", "params": {"speed": 0.3, "intensity": 0.5}},
        ],
        "warm": [
            {"type": "golden_particles", "params": {"speed": 0.4, "count": 50}},
            {"type": "warm_bokeh", "params": {"speed": 0.4, "count": 30}},
            {"type": "sunset_gradient", "params": {"speed": 0.3, "layers": 4}},
            {"type": "light_leaks", "params": {"speed": 0.3, "intensity": 0.4}},
        ],
        "energetic": [
            {"type": "neon_grid", "params": {"speed": 2.0, "line_count": 50}},
            {"type": "light_streaks", "params": {"speed": 3.0, "count": 20}},
            {"type": "gradient_waves", "params": {"speed": 2.0, "layers": 6}},
        ],
        "chill": [
            {"type": "aurora", "params": {"speed": 0.4, "intensity": 0.6}},
            {"type": "floating_dust", "params": {"speed": 0.3, "count": 50}},
            {"type": "warm_gradient", "params": {"speed": 0.3, "layers": 4}},
            {"type": "bokeh", "params": {"speed": 0.3, "count": 30}},
        ],
    }
    
    # Visualization styles per mood
    viz_configs = {
        "dance": [
            {"type": "circular_spectrum", "params": {"bars": 64, "radius": 0.15}},
            {"type": "vertical_bars", "params": {"bars": 48}},
            {"type": "waveform", "params": {"style": "fill"}},
        ],
        "happy": [
            {"type": "circular_spectrum", "params": {"bars": 48, "radius": 0.12}},
            {"type": "horizontal_equalizer", "params": {"bars": 32}},
        ],
        "sad": [
            {"type": "minimal_spectrum", "params": {"bars": 24, "opacity": 0.3}},
            {"type": "waveform", "params": {"style": "thin_line", "opacity": 0.4}},
        ],
        "melancholic": [
            {"type": "minimal_spectrum", "params": {"bars": 20, "opacity": 0.25}},
            {"type": "waveform", "params": {"style": "thin_line", "opacity": 0.3}},
        ],
        "acoustic": [
            {"type": "minimal_spectrum", "params": {"bars": 32, "opacity": 0.4}},
            {"type": "circular_spectrum", "params": {"bars": 36, "radius": 0.1}},
        ],
        "lofi": [
            {"type": "minimal_spectrum", "params": {"bars": 28, "opacity": 0.3}},
            {"type": "horizontal_equalizer", "params": {"bars": 20, "opacity": 0.4}},
        ],
        "romantic": [
            {"type": "circular_spectrum", "params": {"bars": 40, "radius": 0.1, "opacity": 0.5}},
            {"type": "minimal_spectrum", "params": {"bars": 24, "opacity": 0.35}},
        ],
        "epic": [
            {"type": "circular_spectrum", "params": {"bars": 80, "radius": 0.2}},
            {"type": "vertical_bars", "params": {"bars": 64}},
        ],
        "ambient": [
            {"type": "minimal_spectrum", "params": {"bars": 16, "opacity": 0.2}},
        ],
        "warm": [
            {"type": "circular_spectrum", "params": {"bars": 36, "radius": 0.1, "opacity": 0.5}},
            {"type": "minimal_spectrum", "params": {"bars": 24, "opacity": 0.35}},
        ],
        "energetic": [
            {"type": "circular_spectrum", "params": {"bars": 72, "radius": 0.18}},
            {"type": "vertical_bars", "params": {"bars": 56}},
        ],
        "chill": [
            {"type": "minimal_spectrum", "params": {"bars": 24, "opacity": 0.35}},
            {"type": "waveform", "params": {"style": "fill", "opacity": 0.5}},
        ],
    }
    
    # Font selection per mood
    font_map = {
        "dance": "bold_sans",
        "happy": "modern_sans",
        "sad": "elegant_serif",
        "melancholic": "elegant_serif",
        "acoustic": "rounded",
        "lofi": "rounded",
        "romantic": "elegant_serif",
        "epic": "elegant_serif",
        "ambient": "rounded",
        "warm": "rounded",
        "energetic": "bold_sans",
        "chill": "clean_sans",
    }
    
    bg = random.choice(bg_configs.get(mood, bg_configs["chill"]))
    viz = random.choice(viz_configs.get(mood, viz_configs["chill"]))
    font_key = font_map.get(mood, "modern_sans")
    
    # Font sizes based on energy and mood
    if mood in ("sad", "melancholic", "ambient"):
        font_size_lyrics = 52
        font_size_title = 64
    elif mood in ("dance", "energetic", "epic"):
        font_size_lyrics = 60
        font_size_title = 72
    else:
        font_size_lyrics = 56
        font_size_title = 68
    
    # Font color — high contrast with background
    if mood in ("dance", "energetic", "epic"):
        font_color = "#FFFFFF"
        outline = "#000000"
    elif mood in ("sad", "melancholic", "ambient", "lofi"):
        font_color = "#E8E8E8"
        outline = "#1A1A2E"
    else:
        font_color = "#FFFFFF"
        outline = palette[0] if palette else "#000000"
    
    # Transitions
    transitions = {
        "dance": "slide_fade",
        "happy": "pop_in",
        "sad": "slow_fade",
        "melancholic": "slow_fade",
        "acoustic": "gentle_fade",
        "lofi": "slow_fade",
        "romantic": "soft_grow",
        "epic": "zoom_in",
        "ambient": "dissolve",
        "warm": "gentle_fade",
        "energetic": "slide_fade",
        "chill": "dissolve",
    }
    
    # Particle types
    particle_map = {
        "dance": "sparkles",
        "happy": "bubbles",
        "sad": "rain_drops",
        "melancholic": "dust_motes",
        "acoustic": "golden_dust",
        "lofi": "fireflies",
        "romantic": "floating_hearts",
        "epic": "cosmic_dust",
        "ambient": "floating_dust",
        "warm": "golden_dust",
        "energetic": "light_streaks",
        "chill": "floating_dust",
    }
    
    description = f"{mood.title()} mood with {bg['type'].replace('_', ' ')} background, {viz['type'].replace('_', ' ')} visualization, and {font_key.replace('_', ' ')} typography. Color palette: {' → '.join(palette[:3])}."
    
    return VisualStyle(
        mood=mood,
        palette=palette,
        bg_type=bg["type"],
        bg_params=bg["params"],
        viz_type=viz["type"],
        viz_params=viz["params"],
        font_primary=resolve_font(font_key),
        font_secondary=resolve_font("modern_sans"),
        font_size_lyrics=font_size_lyrics,
        font_size_title=font_size_title,
        font_color=font_color,
        font_outline=outline,
        font_shadow=True,
        transition_type=transitions.get(mood, "dissolve"),
        particle_type=particle_map.get(mood, "floating_dust"),
        particle_count=random.randint(20, 80),
        gradient_direction=random.choice(["vertical", "horizontal", "diagonal", "radial"]),
        blur_amount=0.0 if energy > 0.5 else random.uniform(2, 8),
        glow_intensity=random.uniform(0.3, 0.8),
        vignette=mood in ("sad", "melancholic", "epic", "romantic", "ambient"),
        film_grain=random.uniform(0.0, 0.15) if mood in ("lofi", "acoustic", "romantic", "sad") else 0.0,
        light_leak=mood in ("romantic", "warm", "acoustic", "epic"),
        letterbox=mood in ("epic", "melancholic", "cinematic"),
        description=description,
    )