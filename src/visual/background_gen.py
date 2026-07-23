"""
Animated Background Generator
Creates procedural animated 4K backgrounds matching the song's mood.
Each background is a seamless loop rendered as a video stream.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.patches import Circle, FancyBboxPatch
import matplotlib.patheffects as path_effects
from pathlib import Path
import colorsys
import random
import math
import os

# Use ffmpeg-full if available
_ffmpeg_full = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
if os.path.exists(_ffmpeg_full):
    plt.rcParams['animation.ffmpeg_path'] = _ffmpeg_full


def hex_to_rgb(hex_color):
    """Convert hex to RGB tuple (0-1)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def hex_to_hsv(hex_color):
    """Convert hex to HSV."""
    r, g, b = hex_to_rgb(hex_color)
    return colorsys.rgb_to_hsv(r, g, b)


def generate_background(bg_type, palette, params, duration, output_path,
                        width=3840, height=2160, fps=30):
    """Generate animated background video."""
    output_path = str(output_path)
    
    # Use 1920x1080 for render speed, upscale later
    render_w, render_h = 1920, 1080
    render_fps = 30
    
    fig, ax = plt.subplots(figsize=(render_w / 100, render_h / 100), dpi=100)
    fig.patch.set_facecolor('#000000')
    ax.set_xlim(0, render_w)
    ax.set_ylim(0, render_h)
    ax.set_aspect('equal')
    ax.axis('off')
    
    total_frames = int(duration * render_fps)
    
    # Select generator
    generators = {
        "neon_grid": gen_neon_grid,
        "audio_reactive_bars": gen_audio_bars,
        "neon_pulses": gen_neon_pulses,
        "gradient_waves": gen_gradient_waves,
        "gradient_flow": gen_gradient_flow,
        "floating_bubbles": gen_floating_bubbles,
        "sunburst": gen_sunburst,
        "rain_window": gen_rain_window,
        "slow_fog": gen_slow_fog,
        "drifting_clouds": gen_drifting_clouds,
        "ink_spread": gen_ink_spread,
        "floating_dust": gen_floating_dust,
        "golden_particles": gen_golden_particles,
        "warm_gradient": gen_warm_gradient,
        "sunrise": gen_sunrise,
        "city_lights": gen_city_lights,
        "night_sky": gen_night_sky,
        "bokeh": gen_bokeh,
        "floating_hearts": gen_floating_hearts,
        "warm_bokeh": gen_warm_bokeh,
        "light_leaks": gen_light_leaks,
        "sunset_gradient": gen_sunset_gradient,
        "space_nebula": gen_space_nebula,
        "mountain_silhouette": gen_mountains,
        "aurora": gen_aurora,
        "cosmic_dust": gen_cosmic_dust,
        "slow_gradient": gen_slow_gradient,
        "light_streaks": gen_light_streaks,
        "falling_petals": gen_falling_petals,
    }
    
    gen_func = generators.get(bg_type, gen_slow_fog)
    
    # Initialize state
    state = gen_func(ax, palette, params, render_w, render_h, total_frames, init=True)
    
    def update(frame):
        ax.clear()
        ax.set_xlim(0, render_w)
        ax.set_ylim(0, render_h)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#000000')
        gen_func(ax, palette, params, render_w, render_h, total_frames,
                frame=frame, state=state)
        return []
    
    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/render_fps, blit=False)
    
    writer = FFMpegWriter(fps=render_fps, 
                         extra_args=['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                                    '-crf', '18', '-preset', 'fast'])
    
    anim.save(output_path, writer=writer, dpi=100, savefig_kwargs={'facecolor': '#000000'})
    plt.close(fig)
    return output_path


# ═══════════════════════════════════════════════════
# BACKGROUND GENERATORS
# Each returns a state dict on init=True, draws on each frame
# ═══════════════════════════════════════════════════

def _init_particles(count, w, h, speed_range=(0.5, 2.0), size_range=(2, 15)):
    """Initialize particle state."""
    return {
        'x': np.random.uniform(0, w, count),
        'y': np.random.uniform(0, h, count),
        'vx': np.random.uniform(-speed_range[1], speed_range[1], count),
        'vy': np.random.uniform(-speed_range[1], speed_range[1], count),
        'size': np.random.uniform(size_range[0], size_range[1], count),
        'alpha': np.random.uniform(0.2, 0.9, count),
        'phase': np.random.uniform(0, 2 * np.pi, count),
    }


def gen_audio_bars(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Audio-reactive bars — dance."""
    count = params.get('count', 64)
    speed = params.get('speed', 1.5)
    if init:
        return {'phases': np.random.uniform(0, 2*np.pi, count)}
    
    bar_width = w / count
    t = frame * speed / 30.0
    
    # Background gradient
    for i in range(3):
        ax.add_patch(FancyBboxPatch((0, 0), w, h * (1 - i * 0.3),
                     facecolor=palette[i % len(palette)], alpha=0.05, edgecolor='none', zorder=0))
    
    for i in range(count):
        height_factor = 0.3 + 0.5 * abs(np.sin(t + state['phases'][i]))
        bar_h = h * height_factor
        x = i * bar_width
        color = palette[i % len(palette)]
        ax.add_patch(FancyBboxPatch((x + 2, 0), bar_width - 4, bar_h,
                     facecolor=color, alpha=0.4, edgecolor='none', zorder=2))


def gen_neon_pulses(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Neon pulsing circles — dance/energetic."""
    count = params.get('count', 12)
    speed = params.get('speed', 2.0)
    if init:
        return {'phases': np.random.uniform(0, 2*np.pi, count),
                'positions': np.random.uniform(0.15, 0.85, (count, 2))}
    
    t = frame * speed / 30.0
    
    for i in range(count):
        x = state['positions'][i][0] * w
        y = state['positions'][i][1] * h
        pulse = (np.sin(t * 0.5 + state['phases'][i]) * 0.5 + 0.5)
        radius = 50 + pulse * 200
        color = palette[i % len(palette)]
        for r in range(5):
            ax.add_patch(Circle((x, y), radius * (1 + r * 0.2), 
                         facecolor=color, alpha=0.03, edgecolor=color, linewidth=2, zorder=2))


def gen_neon_grid(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Neon perspective grid — dance/energetic."""
    if init:
        return {}
    speed = params.get('speed', 2.0)
    line_count = params.get('line_count', 40)
    t = frame * speed / 30.0
    
    # Gradient background
    for i in range(3):
        color = palette[i % len(palette)]
        ax.add_patch(FancyBboxPatch((0, 0), w, h * (1 - i * 0.3),
                     facecolor=color, alpha=0.15, edgecolor='none', zorder=0))
    
    # Perspective grid lines
    c1 = palette[0]
    c2 = palette[1] if len(palette) > 1 else palette[0]
    
    # Horizontal lines (perspective)
    for i in range(line_count):
        progress = ((i + t * 0.1) % line_count) / line_count
        y = h * 0.5 + (h * 0.5) * (progress ** 2)
        alpha = progress * 0.6
        ax.plot([0, w], [y, y], color=c1, alpha=alpha, linewidth=1.5, zorder=1)
    
    # Vertical lines (perspective converging)
    vanish_x = w / 2
    vanish_y = h * 0.5
    for i in range(-20, 21):
        x_bottom = w / 2 + i * w / 20
        ax.plot([x_bottom, vanish_x], [0, vanish_y], color=c2, alpha=0.3, linewidth=1, zorder=1)
    
    # Glow at vanishing point
    for r in range(100, 0, -10):
        ax.add_patch(Circle((vanish_x, vanish_y), r, facecolor=c1, alpha=0.01, edgecolor='none', zorder=2))


def gen_gradient_waves(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Layered gradient waves — energetic."""
    if init:
        return {}
    speed = params.get('speed', 2.0)
    layers = params.get('layers', 5)
    t = frame * speed / 30.0
    
    x = np.linspace(0, w, 200)
    
    for layer in range(layers):
        color = palette[layer % len(palette)]
        amplitude = h * 0.15 * (1 - layer / layers)
        offset = h * 0.3 + layer * h * 0.12
        wave = offset + amplitude * np.sin(x / w * 4 * np.pi + t + layer * 0.5)
        ax.fill_between(x, 0, wave, color=color, alpha=0.25, zorder=layer+1)


def gen_gradient_flow(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Flowing gradient — happy."""
    if init:
        return {}
    speed = params.get('speed', 1.2)
    layers = params.get('layers', 4)
    t = frame * speed / 30.0
    
    for i in range(layers):
        color = palette[i % len(palette)]
        offset = (t + i * h / layers) % h
        ax.add_patch(FancyBboxPatch((0, offset - h/layers), w, h/layers * 2,
                     facecolor=color, alpha=0.2, edgecolor='none', zorder=i))


def gen_floating_bubbles(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Floating bubbles — happy."""
    count = params.get('count', 30)
    speed = params.get('speed', 1.0)
    if init:
        return _init_particles(count, w, h, speed_range=(0, speed), size_range=(10, 80))
    
    for i in range(count):
        x = state['x'][i]
        y = (state['y'][i] + frame * speed * state['vy'][i] * 0.5) % h
        size = state['size'][i] * 3
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.3
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=alpha, edgecolor=color, linewidth=1, zorder=2))


def gen_sunburst(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Sunburst rays — happy."""
    if init:
        return {}
    speed = params.get('speed', 0.8)
    rays = params.get('rays', 12)
    t = frame * speed / 30.0
    
    cx, cy = w / 2, h / 2
    for i in range(rays):
        angle = 2 * np.pi * i / rays + t * 0.05
        color = palette[i % len(palette)]
        x_end = cx + 1500 * np.cos(angle)
        y_end = cy + 1500 * np.sin(angle)
        ax.plot([cx, x_end], [cy, y_end], color=color, alpha=0.15, linewidth=60, solid_capstyle='round', zorder=1)
    
    # Center glow
    for r in range(300, 0, -20):
        ax.add_patch(Circle((cx, cy), r, facecolor=palette[0], alpha=0.005, edgecolor='none', zorder=2))


def gen_rain_window(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Rain on window — sad/lofi."""
    count = 200
    if init:
        return {
            'drops': _init_particles(count, w, h, speed_range=(3, 8), size_range=(1, 3)),
            'splashes': [],
        }
    
    intensity = params.get('intensity', 0.7)
    speed = params.get('speed', 0.5)
    
    # Background gradient (dark blue)
    for i in range(3):
        ax.add_patch(FancyBboxPatch((0, 0), w, h * (1 - i * 0.3),
                     facecolor=palette[i % len(palette)], alpha=0.1, edgecolor='none', zorder=0))
    
    # Rain drops
    for i in range(int(count * intensity)):
        x = state['drops']['x'][i]
        y = (state['drops']['y'][i] - frame * speed * 15) % h
        length = state['drops']['size'][i] * 8
        ax.plot([x, x - 2], [y, y + length], color='#AABBDD', alpha=0.4, linewidth=1, zorder=2)


def gen_slow_fog(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Slow drifting fog — sad/melancholic."""
    if init:
        return _init_particles(8, w, h, speed_range=(0.1, 0.3), size_range=(200, 500))
    
    density = params.get('density', 0.6)
    speed = params.get('speed', 0.3)
    t = frame * speed / 30.0
    
    for i in range(8):
        x = state['x'][i] + np.sin(t + i) * 50
        y = state['y'][i] + np.cos(t + i * 0.7) * 30
        size = state['size'][i]
        color = palette[i % len(palette)]
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=0.05 * density, edgecolor='none', zorder=2))


def gen_drifting_clouds(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Drifting clouds — sad/melancholic."""
    count = params.get('count', 8)
    speed = params.get('speed', 0.3)
    if init:
        return _init_particles(count, w, h, speed_range=(0.2, 0.5), size_range=(100, 300))
    
    for i in range(count):
        x = (state['x'][i] + frame * speed * state['vx'][i] * 3) % (w + 400) - 200
        y = state['y'][i]
        size = state['size'][i]
        color = palette[i % len(palette)]
        for j in range(5):
            ox = np.sin(j * 1.5) * size * 0.4
            oy = np.cos(j * 1.5) * size * 0.2
            ax.add_patch(Circle((x + ox, y + oy), size * 0.6, facecolor=color, alpha=0.06, edgecolor='none', zorder=2))


def gen_ink_spread(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Ink slowly spreading — melancholic."""
    count = 5
    if init:
        return _init_particles(count, w, h, speed_range=(0, 0), size_range=(50, 150))
    speed = params.get('speed', 0.2)
    t = frame * speed / 30.0
    
    for i in range(count):
        x = state['x'][i]
        y = state['y'][i]
        size = state['size'][i] + t * 50 * (1 + i * 0.2)
        size = min(size, 600)
        color = palette[i % len(palette)]
        alpha = max(0.02, 0.1 - t * 0.005)
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=alpha, edgecolor='none', zorder=2))


def gen_floating_dust(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Floating dust particles — acoustic/ambient/chill."""
    count = params.get('count', 60)
    speed = params.get('speed', 0.4)
    if init:
        return _init_particles(count, w, h, speed_range=(0.2, 1.0), size_range=(1, 5))
    
    # Dark background with slight gradient
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#050508', alpha=1, edgecolor='none', zorder=0))
    
    for i in range(count):
        x = state['x'][i] + np.sin(frame * 0.01 + state['phase'][i]) * 30
        y = (state['y'][i] + frame * speed * state['vy'][i]) % h
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.5
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=alpha, edgecolor='none', zorder=2))


def gen_golden_particles(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Golden floating particles — warm/acoustic/romantic."""
    count = params.get('count', 50)
    speed = params.get('speed', 0.4)
    if init:
        return _init_particles(count, w, h, speed_range=(0.1, 0.5), size_range=(2, 8))
    
    # Warm dark background
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#0A0805', alpha=1, edgecolor='none', zorder=0))
    
    for i in range(count):
        x = state['x'][i] + np.sin(frame * 0.02 + state['phase'][i]) * 40
        y = (state['y'][i] + frame * speed * abs(state['vy'][i])) % h
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.7
        # Glow
        for r in range(3):
            ax.add_patch(Circle((x, y), size * (1 + r), facecolor=color, alpha=alpha * (0.3 / (r + 1)), edgecolor='none', zorder=2))


def gen_warm_gradient(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Warm gradient — acoustic/warm."""
    if init:
        return {}
    speed = params.get('speed', 0.5)
    layers = params.get('layers', 3)
    t = frame * speed / 30.0
    
    for i in range(layers):
        color = palette[i % len(palette)]
        offset = np.sin(t * 0.5 + i) * 0.1
        ax.add_patch(FancyBboxPatch((0, 0), w, h * (0.5 + offset + i * 0.2),
                     facecolor=color, alpha=0.15, edgecolor='none', zorder=i+1))


def gen_sunrise(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Sunrise gradient — acoustic."""
    if init:
        return {}
    speed = params.get('speed', 0.3)
    t = frame * speed / 30.0
    sun_y = h * 0.3 + np.sin(t * 0.1) * h * 0.1
    
    # Sky gradient
    for i in range(5):
        y = h * i / 5
        color = palette[i % len(palette)]
        ax.add_patch(FancyBboxPatch((0, y), w, h / 5, facecolor=color, alpha=0.15, edgecolor='none', zorder=i))
    
    # Sun glow
    for r in range(400, 0, -20):
        ax.add_patch(Circle((w / 2, sun_y), r, facecolor=palette[0], alpha=0.005, edgecolor='none', zorder=10))


def gen_city_lights(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """City lights at night — lofi."""
    count = params.get('count', 40)
    speed = params.get('speed', 0.5)
    if init:
        return _init_particles(count * 3, w, h, speed_range=(0, 0), size_range=(1, 4))
    
    # Dark background
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#0D0D15', alpha=1, edgecolor='none', zorder=0))
    
    # City silhouette
    building_w = 60
    for i in range(0, w, building_w):
        height = 200 + (hash(i) % 300)
        ax.add_patch(FancyBboxPatch((i, 0), building_w - 5, height,
                     facecolor='#1A1A2E', alpha=0.9, edgecolor='none', zorder=1))
        # Windows
        for wy in range(20, height - 20, 30):
            for wx in range(10, building_w - 15, 20):
                if hash(i + wy + wx) % 3 == 0:
                    color = random.choice(palette)
                    ax.add_patch(FancyBboxPatch((i + wx, wy), 8, 12,
                                 facecolor=color, alpha=0.6, edgecolor='none', zorder=2))
    
    # Stars
    for i in range(count * 2):
        x = state['x'][i] % w
        y = state['y'][i] % (h * 0.5) + h * 0.5
        twinkle = np.sin(frame * 0.05 + state['phase'][i]) * 0.5 + 0.5
        ax.add_patch(Circle((x, y), state['size'][i], facecolor='#FFFFFF', alpha=twinkle * 0.6, edgecolor='none', zorder=3))


def gen_night_sky(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Night sky with stars — lofi."""
    stars = params.get('stars', 200)
    if init:
        return _init_particles(stars, w, h, speed_range=(0, 0), size_range=(0.5, 2.5))
    
    speed = params.get('speed', 0.2)
    
    # Dark gradient
    for i in range(3):
        ax.add_patch(FancyBboxPatch((0, 0), w, h * (1 - i * 0.3),
                     facecolor=palette[i % len(palette)], alpha=0.1, edgecolor='none', zorder=0))
    
    for i in range(stars):
        x = state['x'][i]
        y = state['y'][i]
        twinkle = np.sin(frame * 0.03 + state['phase'][i]) * 0.4 + 0.5
        ax.add_patch(Circle((x, y), state['size'][i], facecolor='#FFFFFF', alpha=twinkle * 0.8, edgecolor='none', zorder=2))
    
    # Slow moon glow
    ax.add_patch(Circle((w * 0.75, h * 0.7), 80, facecolor='#F0F0F0', alpha=0.3, edgecolor='none', zorder=2))
    for r in range(200, 80, -20):
        ax.add_patch(Circle((w * 0.75, h * 0.7), r, facecolor='#F0F0F0', alpha=0.01, edgecolor='none', zorder=1))


def gen_bokeh(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Bokeh circles — chill/lofi."""
    count = params.get('count', 30)
    speed = params.get('speed', 0.3)
    if init:
        return _init_particles(count, w, h, speed_range=(0.1, 0.5), size_range=(20, 80))
    
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#0A0A12', alpha=1, edgecolor='none', zorder=0))
    
    for i in range(count):
        x = state['x'][i] + np.sin(frame * 0.01 + state['phase'][i]) * 20
        y = (state['y'][i] + frame * speed * state['vy'][i]) % h
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.2
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=alpha, edgecolor=color, linewidth=2, zorder=2))


def gen_floating_hearts(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Floating hearts — romantic."""
    count = params.get('count', 15)
    speed = params.get('speed', 0.5)
    if init:
        return _init_particles(count, w, h, speed_range=(0.2, 0.6), size_range=(10, 30))
    
    for i in range(count):
        x = state['x'][i] + np.sin(frame * 0.03 + state['phase'][i]) * 30
        y = (state['y'][i] + frame * speed * state['vy'][i]) % h
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.4
        # Draw heart shape
        t_heart = np.linspace(0, 2 * np.pi, 30)
        hx = size * 16 * np.sin(t_heart) ** 3 / 16
        hy = -size * (13 * np.cos(t_heart) - 5 * np.cos(2*t_heart) - 2 * np.cos(3*t_heart) - np.cos(4*t_heart)) / 16
        ax.fill(x + hx, y + hy, color=color, alpha=alpha, zorder=2)


def gen_warm_bokeh(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Warm bokeh — romantic/warm."""
    count = params.get('count', 30)
    speed = params.get('speed', 0.4)
    if init:
        return _init_particles(count, w, h, speed_range=(0.1, 0.4), size_range=(15, 60))
    
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#0A0608', alpha=1, edgecolor='none', zorder=0))
    
    for i in range(count):
        x = state['x'][i] + np.sin(frame * 0.02 + state['phase'][i]) * 25
        y = (state['y'][i] + frame * speed * abs(state['vy'][i])) % h
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.25
        # Glow
        for r in range(3):
            ax.add_patch(Circle((x, y), size * (1 + r * 0.5), facecolor=color, alpha=alpha / (r + 1), edgecolor='none', zorder=2))


def gen_light_leaks(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Cinematic light leaks — romantic/epic."""
    if init:
        return _init_particles(5, w, h, speed_range=(0.05, 0.2), size_range=(100, 300))
    intensity = params.get('intensity', 0.5)
    speed = params.get('speed', 0.3)
    t = frame * speed / 30.0
    
    # Dark base
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#080810', alpha=1, edgecolor='none', zorder=0))
    
    for i in range(5):
        x = state['x'][i] + np.sin(t + i * 1.5) * 100
        y = state['y'][i] + np.cos(t + i * 0.8) * 80
        size = state['size'][i]
        color = palette[i % len(palette)]
        for r in range(5):
            ax.add_patch(Circle((x, y), size * (1 + r), facecolor=color, alpha=intensity * 0.02, edgecolor='none', zorder=2))


def gen_sunset_gradient(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Sunset gradient — warm/romantic."""
    if init:
        return {}
    speed = params.get('speed', 0.3)
    layers = params.get('layers', 4)
    t = frame * speed / 30.0
    
    for i in range(layers):
        color = palette[i % len(palette)]
        offset = h * (0.3 + i * 0.2) + np.sin(t * 0.3 + i) * 20
        ax.add_patch(FancyBboxPatch((0, 0), w, offset,
                     facecolor=color, alpha=0.15, edgecolor='none', zorder=i+1))


def gen_space_nebula(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Space nebula — epic."""
    stars = params.get('stars', 300)
    if init:
        return {
            'stars': _init_particles(stars, w, h, speed_range=(0, 0), size_range=(0.5, 3)),
            'clouds': _init_particles(8, w, h, speed_range=(0.05, 0.2), size_range=(200, 500)),
        }
    speed = params.get('speed', 0.5)
    t = frame * speed / 30.0
    
    # Deep space background
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#020015', alpha=1, edgecolor='none', zorder=0))
    
    # Nebula clouds
    for i in range(8):
        x = state['clouds']['x'][i] + np.sin(t * 0.1 + i) * 50
        y = state['clouds']['y'][i] + np.cos(t * 0.08 + i) * 40
        size = state['clouds']['size'][i]
        color = palette[i % len(palette)]
        for r in range(5):
            ax.add_patch(Circle((x, y), size * (1 + r * 0.5), facecolor=color, alpha=0.03, edgecolor='none', zorder=1))
    
    # Stars
    for i in range(stars):
        x = state['stars']['x'][i]
        y = state['stars']['y'][i]
        twinkle = np.sin(t * 0.5 + state['stars']['phase'][i]) * 0.4 + 0.5
        ax.add_patch(Circle((x, y), state['stars']['size'][i], facecolor='#FFFFFF', alpha=twinkle * 0.8, edgecolor='none', zorder=3))


def gen_mountains(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Mountain silhouettes — epic."""
    if init:
        return {}
    speed = params.get('speed', 0.3)
    layers = params.get('layers', 5)
    t = frame * speed / 30.0
    
    # Sky gradient
    for i in range(5):
        ax.add_patch(FancyBboxPatch((0, h * (0.3 + i * 0.14)), w, h * 0.2,
                     facecolor=palette[i % len(palette)], alpha=0.1, edgecolor='none', zorder=0))
    
    # Mountain layers (back to front)
    for layer in range(layers):
        color = palette[layer % len(palette)]
        alpha = 0.3 + layer * 0.15
        base_y = h * (0.2 + layer * 0.12)
        x = np.linspace(0, w, 50)
        y = base_y + 100 * np.sin(x / 200 + t * 0.1 + layer) * (1 - layer / layers)
        ax.fill_between(x, 0, y, color=color, alpha=alpha, zorder=layer + 2)


def gen_aurora(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Aurora borealis — epic/chill/ambient."""
    if init:
        return {}
    speed = params.get('speed', 0.4)
    intensity = params.get('intensity', 0.6)
    t = frame * speed / 30.0
    
    # Dark sky
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#020210', alpha=1, edgecolor='none', zorder=0))
    
    # Stars
    for i in range(100):
        x = (i * 137.5) % w
        y = (i * 73.3) % h
        twinkle = np.sin(t * 0.5 + i) * 0.3 + 0.4
        ax.add_patch(Circle((x, y), 1, facecolor='#FFFFFF', alpha=twinkle, edgecolor='none', zorder=1))
    
    # Aurora bands
    x = np.linspace(0, w, 200)
    for band in range(3):
        color = palette[band % len(palette)]
        for offset in range(0, 200, 5):
            wave_y = h * 0.5 + 200 * np.sin(x / 300 + t + band) + offset * np.sin(t * 0.3 + band)
            ax.plot(x, wave_y, color=color, alpha=intensity * 0.02, linewidth=50, solid_capstyle='round', zorder=2)


def gen_cosmic_dust(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Cosmic dust particles — epic."""
    count = params.get('count', 200)
    speed = params.get('speed', 0.4)
    if init:
        return _init_particles(count, w, h, speed_range=(0.1, 0.8), size_range=(1, 5))
    
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#030014', alpha=1, edgecolor='none', zorder=0))
    
    cx, cy = w / 2, h / 2
    for i in range(count):
        angle = state['phase'][i] + frame * 0.005
        dist = np.sqrt(state['x'][i]**2 + state['y'][i]**2) % max(w, h)
        x = cx + dist * np.cos(angle) * 0.5
        y = cy + dist * np.sin(angle) * 0.5
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.4
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=alpha, edgecolor='none', zorder=2))


def gen_slow_gradient(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Slowly shifting gradient — ambient."""
    if init:
        return {}
    speed = params.get('speed', 0.2)
    layers = params.get('layers', 3)
    t = frame * speed / 30.0
    
    for i in range(layers):
        color = palette[i % len(palette)]
        r = np.sin(t * 0.3 + i * 1.2) * 0.5 + 0.5
        ax.add_patch(Circle((w * (0.3 + r * 0.4), h * (0.3 + (1-r) * 0.4)), 800,
                     facecolor=color, alpha=0.05, edgecolor='none', zorder=i+1))


def gen_light_streaks(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Light streaks — energetic."""
    count = params.get('count', 20)
    speed = params.get('speed', 3.0)
    if init:
        return _init_particles(count, w, h, speed_range=(1, 3), size_range=(50, 200))
    
    ax.add_patch(FancyBboxPatch((0, 0), w, h, facecolor='#050505', alpha=1, edgecolor='none', zorder=0))
    
    for i in range(count):
        x = state['x'][i] + frame * speed * state['vx'][i] * 3
        y = state['y'][i]
        x = x % (w + 400) - 200
        length = state['size'][i]
        color = palette[i % len(palette)]
        ax.plot([x, x + length], [y, y], color=color, alpha=0.3, linewidth=3, solid_capstyle='round', zorder=2)


def gen_falling_petals(ax, palette, params, w, h, total_frames, frame=0, state=None, init=False):
    """Falling petals — sad/romantic."""
    count = params.get('count', 20)
    speed = params.get('speed', 0.6)
    if init:
        return _init_particles(count, w, h, speed_range=(0.3, 0.8), size_range=(5, 15))
    
    for i in range(count):
        x = state['x'][i] + np.sin(frame * 0.03 + state['phase'][i]) * 50
        y = (state['y'][i] - frame * speed * state['vy'][i] * 3) % h
        size = state['size'][i]
        color = palette[i % len(palette)]
        alpha = state['alpha'][i] * 0.5
        # Petal shape
        ax.add_patch(Circle((x, y), size, facecolor=color, alpha=alpha, edgecolor='none', zorder=2))
        ax.add_patch(Circle((x + size * 0.7, y), size * 0.7, facecolor=color, alpha=alpha * 0.7, edgecolor='none', zorder=2))