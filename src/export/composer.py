"""
Video Composition Engine
Composites background, audio visualization, lyrics, and branding into final video.
Uses ffmpeg filter_complex for layering.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional

# Use ffmpeg-full if available (has drawtext, subtitles, ass support)
FFMPEG_BIN = "ffmpeg"
FFMPEG_FULL = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
if Path(FFMPEG_FULL).exists():
    FFMPEG_BIN = FFMPEG_FULL


def compose_video(
    audio_path: str,
    background_path: str,
    ass_subtitle_path: str,
    output_path: str,
    style_config: dict,
    song_title: str = "",
    artist_name: str = "",
    channel_name: str = "",
    duration: float = 0,
    width: int = 3840,
    height: int = 2160,
    fps: int = 30,
    with_viz: bool = True,
    viz_config: dict = None,
    logo_path: str = None,
    show_subscribe: bool = True,
) -> str:
    """
    Compose the final karaoke video using ffmpeg.
    Layers: background → vignette/grain → audio viz → lyrics → branding
    """
    audio_path = str(audio_path)
    background_path = str(background_path)
    ass_subtitle_path = str(ass_subtitle_path)
    output_path = str(output_path)
    
    palette = style_config.get("palette", ["#3A86FF", "#FF006E", "#FFBE0B"])
    viz_type = viz_config.get("type", "circular_spectrum") if viz_config else "circular_spectrum"
    viz_params = viz_config.get("params", {}) if viz_config else {}
    
    # Build the filter complex
    filters = []
    filter_idx = 0
    
    # === INPUT 0: background video ===
    # Scale to target resolution
    filters.append(f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1[bg]")
    
    # === Apply visual effects based on style ===
    blur_amount = style_config.get("blur_amount", 0)
    vignette = style_config.get("vignette", False)
    film_grain = style_config.get("film_grain", 0)
    light_leak = style_config.get("light_leak", False)
    glow_intensity = style_config.get("glow_intensity", 0.5)
    
    bg_chain = ""
    current_label = "[bg]"
    next_label_num = 0
    
    def next_label():
        nonlocal next_label_num
        next_label_num += 1
        return f"[bg_{next_label_num}]"
    
    bg_parts = []
    
    if blur_amount > 0:
        out = next_label()
        bg_parts.append(f"{current_label}gblur=sigma={blur_amount}{out}")
        current_label = out
    
    if vignette:
        out = next_label()
        bg_parts.append(f"{current_label}vignette=PI/4{out}")
        current_label = out
    
    if film_grain > 0:
        noise_strength = int(film_grain * 30)
        out = next_label()
        bg_parts.append(f"{current_label}noise=alls={noise_strength}:allf=t+0{out}")
        current_label = out
    
    if bg_parts:
        filters.append(",".join(bg_parts))
    bg_final = current_label
    
    # === INPUT 1: audio → visualization ===
    if with_viz:
        viz_filter = build_viz_filter(viz_type, viz_params, palette, width, height, style_config)
        filters.append(viz_filter)
        viz_name = "[viz]"
    else:
        viz_name = "[bg_noviz]"
    
    # === Overlay visualization on background ===
    if with_viz:
        filters.append(f"{bg_final}[viz]overlay=(W-w)/2:(H-h)/2:format=auto[viz_bg]")
        bg_final = "[viz_bg]"
    
    # === Subtitles (lyrics) ===
    # ASS subtitles with fontsdir — check file exists and has content
    if not Path(ass_subtitle_path).exists() or Path(ass_subtitle_path).stat().st_size < 50:
        # Create a minimal valid ASS file
        Path(ass_subtitle_path).write_text(
            "[Script Info]\nTitle: Empty\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Helvetica Neue,56,&H00FFFFFF,&H00FFD700,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,2,2,120,120,80,1\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
    
    # Point libass at the directory containing the resolved primary font so it
    # can find it by name; fall back to the macOS system font dir. Cross-platform
    # font resolution happens in style_engine.resolve_font().
    font_primary_path = style_config.get("font_primary", "")
    if font_primary_path and Path(font_primary_path).exists():
        fonts_dir = str(Path(font_primary_path).parent)
    else:
        fonts_dir = "/System/Library/Fonts"
    # Escape colons in path for ffmpeg
    ass_path_escaped = ass_subtitle_path.replace(":", "\\:")
    fonts_dir_escaped = fonts_dir.replace(":", "\\:")
    sub_filter = f"{bg_final}subtitles='{ass_path_escaped}':fontsdir='{fonts_dir_escaped}'"
    filters.append(f"{sub_filter}[lyrics_bg]")
    
    # === Branding overlay (title at start, channel name) ===
    branding_parts = []
    
    # Helper to convert hex colors for ffmpeg (avoid # which is comment char in ffmpeg)
    def ffmpeg_color(hex_col, alpha=None):
        col = hex_col.lstrip('#')
        if alpha is not None:
            return f"0x{col}@{alpha}"
        return f"0x{col}"
    
    # Title card (first 5 seconds)
    if song_title:
        title_text = song_title.replace("'", "\\'").replace(":", "\\:")
        artist_text = artist_name.replace("'", "\\'").replace(":", "\\:")
        
        # Title appears for first 5 seconds, fades out
        title_font = style_config.get("font_primary", "/System/Library/Fonts/HelveticaNeue.ttc")
        title_font_name = get_font_name(title_font)
        title_size = style_config.get("font_size_title", 72)
        artist_size = int(title_size * 0.5)
        
        palette_str = ffmpeg_color(palette[0]) if palette else "white"
        
        # Draw title at bottom for first 5 seconds
        branding_parts.append(
            f"drawtext=fontfile='{title_font}':"
            f"text='{title_text}':"
            f"fontsize={title_size}:"
            f"fontcolor={palette_str}:"
            f"x=(w-text_w)/2:y=h*0.85:"
            f"borderw=4:bordercolor=black:"
            f"alpha='if(lt(t,5),1,if(lt(t,6),6-t,0))'"
        )
        
        if artist_text:
            branding_parts.append(
                f"drawtext=fontfile='{title_font}':"
                f"text='{artist_text}':"
                f"fontsize={artist_size}:"
                f"fontcolor=white:"
                f"x=(w-text_w)/2:y=h*0.85+{title_size+20}:"
                f"borderw=2:bordercolor=black:"
                f"alpha='if(lt(t,5),0.8,if(lt(t,6),0.8*(6-t),0))'"
            )
    
    # Channel name (bottom corner, always visible)
    if channel_name:
        ch_text = channel_name.replace("'", "\\'").replace(":", "\\:")
        ch_font = style_config.get("font_secondary", "/System/Library/Fonts/HelveticaNeue.ttc")
        ch_color = ffmpeg_color(palette[1] if len(palette) > 1 else "#FFFFFF", alpha=0.6)
        branding_parts.append(
            f"drawtext=fontfile='{ch_font}':"
            f"text='{ch_text}':"
            f"fontsize=28:"
            f"fontcolor={ch_color}:"
            f"x=w-text_w-30:y=h-text_h-30:"
            f"borderw=2:bordercolor=black"
        )
    
    # Animated "Subscribe" call-to-action, pulsing during the final ~10 seconds.
    if show_subscribe and duration > 12:
        cta_font = style_config.get("font_primary", "/System/Library/Fonts/HelveticaNeue.ttc")
        cta_color = ffmpeg_color(palette[0] if palette else "#FFFFFF")
        cta_start = round(duration - 10.0, 2)
        branding_parts.append(
            f"drawtext=fontfile='{cta_font}':"
            f"text='► SUBSCRIBE':"
            f"fontsize=44:"
            f"fontcolor={cta_color}:"
            f"x=(w-text_w)/2:y=h*0.9:"
            f"borderw=3:bordercolor=black:"
            f"alpha='if(gt(t,{cta_start}),0.2+0.6*abs(sin(2*PI*0.8*t)),0)'"
        )

    if branding_parts:
        branding_chain = "[lyrics_bg]" + ",".join(branding_parts) + "[final]"
        filters.append(branding_chain)
        final_name = "[final]"
    else:
        final_name = "[lyrics_bg]"

    # Optional channel logo overlay (top-right), composited as a third input.
    use_logo = bool(logo_path) and Path(logo_path).exists()
    if use_logo:
        logo_h = int(height * 0.09)
        filters.append(
            f"[2:v]scale=-1:{logo_h},format=rgba,colorchannelmixer=aa=0.85[logo]"
        )
        filters.append(f"{final_name}[logo]overlay=W-w-40:40[branded]")
        final_name = "[branded]"

    # === Build full filter_complex ===
    filter_complex = ";".join(filters)
    
    # === Build ffmpeg command ===
    # The background is a short seamless loop; -stream_loop tiles it to fill the
    # track, and -t (below) trims to the exact song length. Only loop when we
    # have a real duration to trim against, otherwise an infinite loop would
    # never terminate.
    bg_input_opts = ["-stream_loop", "-1"] if duration > 0 else []
    # Logo is input index 2 (referenced as [2:v] above); loop the still image
    # so it is available for the whole track.
    logo_input = ["-loop", "1", "-i", str(logo_path)] if use_logo else []
    cmd = [
        FFMPEG_BIN, "-y",
        *bg_input_opts,
        "-i", background_path,        # 0: background video (looped)
        "-i", audio_path,             # 1: audio
        *logo_input,                  # 2: logo image (optional)
        "-filter_complex", filter_complex,
        "-map", final_name,
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-c:a", "aac",
        "-b:a", "320k",
        "-movflags", "+faststart",
        "-t", str(duration) if duration > 0 else "-1",
        output_path
    ]
    
    # Remove -t if no duration
    if duration <= 0:
        cmd.remove("-t")
        cmd.remove("-1")
    
    print(f"Running ffmpeg: {' '.join(cmd[:20])}...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    
    if result.returncode != 0:
        print(f"ffmpeg stderr: {result.stderr[-2000:]}")
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
    
    print(f"Video composed: {output_path}")
    return output_path


def build_viz_filter(viz_type: str, params: dict, palette: list,
                     width: int, height: int, style_config: dict) -> str:
    """Build an audio visualization filter for ffmpeg.

    Each visualization type maps to a genuinely distinct ffmpeg source filter
    (rather than every type collapsing to the same waveform):

      * circular_spectrum   -> avectorscope (a circular Lissajous scope)
      * vertical_bars       -> showfreqs bars (full-height frequency bars)
      * horizontal_equalizer-> showfreqs bars (a short, wide equalizer strip)
      * waveform            -> showwaves cline (a centered waveform)
      * minimal_spectrum    -> showwaves line (a thin, subtle line)

    All are alpha-composited over the background at the configured opacity.
    """
    opacity = params.get("opacity", 0.6)
    # Convert hex to 0x format for ffmpeg
    viz_color = "0x" + palette[0].lstrip('#') if palette else "0x3A86FF"
    viz_color2 = "0x" + palette[1].lstrip('#') if len(palette) > 1 else viz_color

    def alpha(o):
        return f"format=rgba,colorchannelmixer=aa={max(0.0, min(1.0, o))}[viz]"

    if viz_type == "circular_spectrum":
        # avectorscope draws a circular oscilloscope from the stereo signal.
        # Kept square and centered by the compositor's overlay, so the black
        # canvas doesn't cover (and darken) the whole frame.
        return (
            f"[1:a]avectorscope=s={height}x{height}:rate=30:mode=lissajous:"
            f"draw=line:scale=cbrt,{alpha(opacity)}"
        )

    elif viz_type == "vertical_bars":
        return (
            f"[1:a]showfreqs=s={width}x{int(height*0.4)}:rate=30:mode=bar:"
            f"ascale=log:fscale=log:colors={viz_color},{alpha(opacity)}"
        )

    elif viz_type == "horizontal_equalizer":
        return (
            f"[1:a]showfreqs=s={int(width*0.7)}x{int(height*0.18)}:rate=30:mode=bar:"
            f"ascale=log:fscale=log:colors={viz_color},"
            f"{alpha(opacity * 0.6)}"
        )

    elif viz_type == "waveform":
        return (
            f"[1:a]showwaves=s={width}x{height}:mode=cline:rate=30:"
            f"colors={viz_color}|{viz_color2},{alpha(opacity)}"
        )

    elif viz_type == "minimal_spectrum":
        opacity = params.get("opacity", 0.3)
        return (
            f"[1:a]showwaves=s={int(width*0.6)}x{int(height*0.15)}:mode=line:rate=30:"
            f"colors={viz_color},{alpha(opacity)}"
        )

    else:
        return (
            f"[1:a]showwaves=s={width}x{height}:mode=cline:rate=30:"
            f"colors={viz_color}|{viz_color2},{alpha(opacity)}"
        )


def get_font_name(font_path: str) -> str:
    """Get a reasonable font name from path."""
    name = Path(font_path).stem
    # Map common system fonts
    mapping = {
        "HelveticaNeue": "Helvetica Neue",
        "Helvetica": "Helvetica",
        "Avenir Next": "Avenir Next",
        "Avenir": "Avenir",
        "AmericanTypewriter": "American Typewriter",
        "Courier": "Courier New",
    }
    return mapping.get(name, name)


def export_shorts_version(input_video: str, output_path: str, duration: float = 0) -> str:
    """Create 9:16 Shorts version from 16:9 video."""
    input_video = str(input_video)
    output_path = str(output_path)
    
    # Crop center, scale to 9:16 (1080x1920)
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_video,
        "-vf", "crop=ih*9/16:ih,scale=1080:1920,setsar=1",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "256k",
        "-movflags", "+faststart",
    ]
    
    if duration > 0:
        cmd.extend(["-t", str(duration)])
    
    cmd.append(output_path)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    
    if result.returncode != 0:
        raise RuntimeError(f"Shorts export failed: {result.stderr[-500:]}")
    
    return output_path


def export_1080p_version(input_video: str, output_path: str) -> str:
    """Create 1080p version from 4K video."""
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", str(input_video),
        "-vf", "scale=1920:1080",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    
    if result.returncode != 0:
        raise RuntimeError(f"1080p export failed: {result.stderr[-500:]}")
    
    return output_path


def generate_thumbnail(
    background_path: str,
    song_title: str,
    artist_name: str,
    style_config: dict,
    output_path: str,
    width: int = 1280,
    height: int = 720,
) -> str:
    """Generate YouTube thumbnail from a frame of the background video."""
    background_path = str(background_path)
    output_path = str(output_path)
    
    palette = style_config.get("palette", ["#3A86FF", "#FF006E", "#FFBE0B"])
    font_primary = style_config.get("font_primary", "/System/Library/Fonts/HelveticaNeue.ttc")
    
    # Extract a representative frame — use 30% into the video
    ffprobe_bin = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    bg_duration_cmd = [
        ffprobe_bin, "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        background_path
    ]
    try:
        dur_result = subprocess.run(bg_duration_cmd, capture_output=True, text=True, timeout=10)
        bg_dur = float(dur_result.stdout.strip()) if dur_result.stdout.strip() else 10.0
    except Exception:
        bg_dur = 10.0
    
    mid_time = max(1.0, bg_dur * 0.3)
    mid_frame = f"{int(mid_time // 3600):02d}:{int((mid_time % 3600) // 60):02d}:{mid_time % 60:02.1f}"
    
    # Build thumbnail with text overlay
    title_text = song_title.replace("'", "\\'").replace(":", "\\:")
    artist_text = artist_name.replace("'", "\\'").replace(":", "\\:")
    
    # Colors in 0x format for ffmpeg
    col0 = "0x" + palette[0].lstrip('#') if palette else "white"
    col1 = "0x" + palette[1].lstrip('#') if len(palette) > 1 else col0
    
    # Gradient overlay for text readability
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"drawbox=x=0:y=0:w={width}:h={height}:color=black@0.3:t=fill,"
        f"drawtext=fontfile='{font_primary}':text='{title_text}':"
        f"fontsize=72:fontcolor=white:borderw=6:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.35,"
        f"drawtext=fontfile='{font_primary}':text='{artist_text}':"
        f"fontsize=40:fontcolor={col0}:borderw=4:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.35+90,"
        f"drawtext=fontfile='{font_primary}':text='♪ KARAOKE':"
        f"fontsize=36:fontcolor={col1}:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.65"
    )
    
    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", mid_frame,
        "-i", background_path,
        "-frames:v", "1",
        "-vf", vf,
        "-q:v", "2",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        # Fallback: just extract the frame
        cmd_fallback = [
            FFMPEG_BIN, "-y",
            "-ss", mid_frame,
            "-i", background_path,
            "-frames:v", "1",
            "-vf", f"scale={width}:{height}",
            "-q:v", "2",
            output_path
        ]
        subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=60)
    
    return output_path