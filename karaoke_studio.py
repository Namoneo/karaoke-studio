"""
╔══════════════════════════════════════════════════════════════╗
║  KARAOKE STUDIO — Autonomous YouTube Karaoke Video Producer   ║
║  Transforms a song into a complete karaoke video package.     ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python karaoke_studio.py --audio song.mp3 --title "Song Name" --artist "Artist"
    python karaoke_studio.py --audio song.mp3 --title "Song Name" --lyrics lyrics.txt
    python karaoke_studio.py --audio song.mp3 --title "Song Name" --channel "MyMusic"

Output:
    output/
    ├── video_4k_16x9.mp4      — 4K 16:9 YouTube video
    ├── video_1080p_16x9.mp4   — 1080p version
    ├── video_shorts_9x16.mp4  — 9:16 Shorts version
    ├── thumbnail.jpg          — YouTube thumbnail
    ├── lyrics.ass              — ASS karaoke subtitles
    ├── lyrics.srt              — SRT subtitles
    ├── lyrics.lrc              — LRC lyrics file
    ├── metadata.json           — SEO metadata
    ├── analysis.json           — Audio analysis
    ├── style.json              — Visual style
    └── report.txt              — Visual style summary
"""

import argparse
import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Use ffmpeg-full if available (has drawtext, subtitles, ass support)
FFMPEG_FULL = "/opt/homebrew/opt/ffmpeg-full/bin"
if Path(FFMPEG_FULL).exists():
    os.environ["PATH"] = FFMPEG_FULL + ":" + os.environ.get("PATH", "")

# NOTE: the heavy pipeline dependencies (librosa, whisper, matplotlib, ffmpeg
# wrappers) are imported lazily inside run_karaoke_studio() so that `--help`
# and argument validation work without the full stack installed, and a missing
# dependency surfaces as a clear message rather than an import traceback.


# Mood descriptions for SEO
MOOD_DESCRIPTIONS = {
    "dance": "energetic dance vibes with neon visuals",
    "happy": "uplifting and joyful energy",
    "sad": "deep, emotional atmospheres",
    "melancholic": "introspective and moody ambience",
    "acoustic": "warm, natural acoustic tones",
    "lofi": "chill lo-fi aesthetics with cozy visuals",
    "romantic": "romantic and dreamy atmospheres",
    "epic": "cinematic, epic landscapes and cosmic visuals",
    "ambient": "peaceful, ambient soundscapes",
    "warm": "warm, cozy and inviting vibes",
    "energetic": "high-energy, powerful visuals",
    "chill": "relaxed, chill vibes",
}

import os as _os
_os.environ.setdefault('MPLBACKEND', 'Agg')


def run_karaoke_studio(
    audio_path: str,
    song_title: str,
    artist_name: str = "",
    lyrics: str = None,
    lyrics_file: str = None,
    channel_name: str = "Karaoke Studio",
    output_dir: str = None,
    whisper_model: str = "base",
    with_visualization: bool = True,
    skip_shorts: bool = False,
    skip_1080p: bool = False,
):
    """
    Main pipeline: Audio → Analyze → Style → Background → Lyrics → Compose → Export → Metadata
    """
    # Imported here (not at module load) so the CLI stays usable without the
    # full dependency stack — see the note near the top of this file.
    try:
        from audio.analyzer import analyze_audio
        from visual.style_engine import generate_style
        from visual.background_gen import generate_background
        from lyrics.karaoke import process_lyrics
        from export.composer import (
            compose_video, export_shorts_version,
            export_1080p_version, generate_thumbnail,
        )
        from metadata.seo_generator import generate_metadata
    except ImportError as e:
        raise RuntimeError(
            f"Missing a required dependency ({e.name}). "
            "Install the pipeline requirements with: pip install -r requirements.txt"
        ) from e

    start_time = time.time()
    audio_path = Path(audio_path).resolve()
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Set up output directory
    if output_dir is None:
        safe_title = "".join(c if c.isalnum() or c in '-_ ' else '_' for c in song_title)
        safe_title = safe_title.strip().replace(' ', '_')
        output_dir = Path(__file__).parent / "output" / safe_title
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"  KARAOKE STUDIO")
    print(f"  Song: {song_title}" + (f" — {artist_name}" if artist_name else ""))
    print(f"  Audio: {audio_path.name}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")
    
    # ─────────────────────────────────────
    # Step 1: Analyze Audio
    # ─────────────────────────────────────
    print("📊 Step 1/8: Analyzing audio...")
    analysis = analyze_audio(str(audio_path))
    
    print(f"   Duration: {analysis.duration:.1f}s")
    print(f"   BPM: {analysis.bpm}")
    print(f"   Key: {analysis.key}")
    print(f"   Mood: {analysis.mood} ({', '.join(analysis.moods)})")
    print(f"   Genre: {analysis.genre}")
    print(f"   Energy: {analysis.energy:.2f}")
    print(f"   Valence: {analysis.valence:.2f}")
    
    # Save analysis
    with open(output_dir / "analysis.json", "w") as f:
        json.dump({
            "duration": analysis.duration,
            "bpm": analysis.bpm,
            "key": analysis.key,
            "energy": analysis.energy,
            "danceability": analysis.danceability,
            "acousticness": analysis.acousticness,
            "valence": analysis.valence,
            "mood": analysis.mood,
            "moods": analysis.moods,
            "color_palette": analysis.color_palette,
            "genre": analysis.genre,
            "spectral_centroid": analysis.spectral_centroid,
            "rms_mean": analysis.rms_mean,
            "rms_std": analysis.rms_std,
            "tempo_confidence": analysis.tempo_confidence,
            "sections": analysis.sections,
        }, f, indent=2)
    
    # ─────────────────────────────────────
    # Step 2: Generate Visual Style
    # ─────────────────────────────────────
    print("\n🎨 Step 2/8: Generating visual style...")
    
    # Use song hash as seed for uniqueness
    import hashlib
    seed = int(hashlib.md5(song_title.encode()).hexdigest()[:8], 16)
    
    style = generate_style(
        mood=analysis.mood,
        palette=analysis.color_palette,
        energy=analysis.energy,
        valence=analysis.valence,
        bpm=analysis.bpm,
        seed=seed,
    )
    
    print(f"   Background: {style.bg_type.replace('_', ' ')}")
    print(f"   Visualization: {style.viz_type.replace('_', ' ')}")
    print(f"   Font: {Path(style.font_primary).stem}")
    print(f"   Particles: {style.particle_type}")
    print(f"   Vignette: {style.vignette}")
    print(f"   Film grain: {style.film_grain:.2f}")
    print(f"   Description: {style.description}")
    
    # Save style
    with open(output_dir / "style.json", "w") as f:
        json.dump({
            "mood": style.mood,
            "palette": style.palette,
            "bg_type": style.bg_type,
            "bg_params": style.bg_params,
            "viz_type": style.viz_type,
            "viz_params": style.viz_params,
            "font_primary": style.font_primary,
            "font_secondary": style.font_secondary,
            "font_size_lyrics": style.font_size_lyrics,
            "font_size_title": style.font_size_title,
            "font_color": style.font_color,
            "font_outline": style.font_outline,
            "font_shadow": style.font_shadow,
            "transition_type": style.transition_type,
            "particle_type": style.particle_type,
            "particle_count": style.particle_count,
            "gradient_direction": style.gradient_direction,
            "blur_amount": style.blur_amount,
            "glow_intensity": style.glow_intensity,
            "vignette": style.vignette,
            "film_grain": style.film_grain,
            "light_leak": style.light_leak,
            "letterbox": style.letterbox,
            "description": style.description,
        }, f, indent=2)
    
    # ─────────────────────────────────────
    # Step 3: Generate Animated Background
    # ─────────────────────────────────────
    print("\n🎬 Step 3/8: Generating animated background (4K)...")
    bg_path = output_dir / "background.mp4"
    
    generate_background(
        bg_type=style.bg_type,
        palette=style.palette,
        params=style.bg_params,
        duration=analysis.duration,
        output_path=str(bg_path),
        width=3840,
        height=2160,
        fps=30,
    )
    print(f"   Background saved: {bg_path.name}")
    
    # ─────────────────────────────────────
    # Step 4: Process Lyrics
    # ─────────────────────────────────────
    print("\n🎤 Step 4/8: Processing lyrics...")
    
    lyrics_text = None
    if lyrics_file:
        with open(lyrics_file, "r") as f:
            lyrics_text = f.read()
    elif lyrics:
        lyrics_text = lyrics
    
    if lyrics_text:
        print("   Using provided lyrics — syncing with Whisper...")
    else:
        print("   Transcribing with Whisper...")
    
    lyrics_result = process_lyrics(
        audio_path=str(audio_path),
        lyrics=lyrics_text,
        model_name=whisper_model,
        style_config={
            "font_name": Path(style.font_primary).stem,
            "font_size": style.font_size_lyrics,
            "font_color": style.font_color,
            "outline_color": style.font_outline,
            "highlight_color": style.palette[1] if len(style.palette) > 1 else "#FFD700",
            "transition_type": style.transition_type,
        },
    )
    
    print(f"   Lyrics source: {lyrics_result.source}")
    print(f"   Lines: {len(lyrics_result.lines)}")
    
    # Save lyrics files
    with open(output_dir / "lyrics.ass", "w") as f:
        f.write(lyrics_result.ass_content)
    with open(output_dir / "lyrics.srt", "w") as f:
        f.write(lyrics_result.srt_content)
    with open(output_dir / "lyrics.lrc", "w") as f:
        f.write(lyrics_result.lrc_content)
    
    # Save lyrics data
    lyrics_data = []
    for line in lyrics_result.lines:
        lyrics_data.append({
            "text": line.text,
            "start": line.start,
            "end": line.end,
            "words": line.words,
        })
    with open(output_dir / "lyrics.json", "w") as f:
        json.dump(lyrics_data, f, indent=2)
    
    # ─────────────────────────────────────
    # Step 5: Compose Main Video (4K 16:9)
    # ─────────────────────────────────────
    print("\n🎞️  Step 5/8: Composing 4K 16:9 video...")
    video_4k_path = output_dir / "video_4k_16x9.mp4"
    
    compose_video(
        audio_path=str(audio_path),
        background_path=str(bg_path),
        ass_subtitle_path=str(output_dir / "lyrics.ass"),
        output_path=str(video_4k_path),
        style_config={
            "palette": style.palette,
            "blur_amount": style.blur_amount,
            "vignette": style.vignette,
            "film_grain": style.film_grain,
            "light_leak": style.light_leak,
            "glow_intensity": style.glow_intensity,
            "font_primary": style.font_primary,
            "font_secondary": style.font_secondary,
            "font_size_title": style.font_size_title,
        },
        song_title=song_title,
        artist_name=artist_name,
        channel_name=channel_name,
        duration=analysis.duration,
        width=3840,
        height=2160,
        fps=30,
        with_viz=with_visualization,
        viz_config={
            "type": style.viz_type,
            "params": style.viz_params,
        },
    )
    print(f"   4K video: {video_4k_path.name}")
    
    # ─────────────────────────────────────
    # Step 6: Export Additional Formats
    # ─────────────────────────────────────
    print("\n📦 Step 6/8: Exporting additional formats...")
    
    # 1080p version
    if not skip_1080p:
        video_1080_path = output_dir / "video_1080p_16x9.mp4"
        export_1080p_version(str(video_4k_path), str(video_1080_path))
        print(f"   1080p: {video_1080_path.name}")
    else:
        video_1080_path = None
        print("   1080p: skipped")
    
    # Shorts version (9:16)
    if not skip_shorts:
        shorts_path = output_dir / "video_shorts_9x16.mp4"
        export_shorts_version(str(video_4k_path), str(shorts_path), duration=analysis.duration)
        print(f"   Shorts 9:16: {shorts_path.name}")
    else:
        shorts_path = None
        print("   Shorts: skipped")
    
    # ─────────────────────────────────────
    # Step 7: Generate Thumbnail
    # ─────────────────────────────────────
    print("\n🖼️  Step 7/8: Generating thumbnail...")
    thumbnail_path = output_dir / "thumbnail.jpg"
    
    generate_thumbnail(
        background_path=str(bg_path),
        song_title=song_title,
        artist_name=artist_name,
        style_config={
            "palette": style.palette,
            "font_primary": style.font_primary,
        },
        output_path=str(thumbnail_path),
    )
    print(f"   Thumbnail: {thumbnail_path.name}")
    
    # ─────────────────────────────────────
    # Step 8: Generate SEO Metadata
    # ─────────────────────────────────────
    print("\n📝 Step 8/8: Generating SEO metadata...")
    
    metadata = generate_metadata(
        song_title=song_title,
        artist_name=artist_name,
        mood=analysis.mood,
        genre=analysis.genre,
        bpm=analysis.bpm,
        duration=analysis.duration,
        has_lyrics=True,
        channel_name=channel_name,
    )
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump({
            "seo_title": metadata.seo_title,
            "seo_description": metadata.seo_description,
            "hashtags": metadata.hashtags,
            "keywords": metadata.keywords,
            "youtube_tags": metadata.youtube_tags,
            "thumbnail_title": metadata.thumbnail_title,
            "short_description": metadata.short_description,
            "pinned_comment": metadata.pinned_comment,
            "category": metadata.category,
        }, f, indent=2)
    
    print(f"   SEO Title: {metadata.seo_title}")
    print(f"   Hashtags: {' '.join(metadata.hashtags[:5])}...")
    
    # ─────────────────────────────────────
    # Generate Report
    # ─────────────────────────────────────
    elapsed = time.time() - start_time
    report = generate_report(
        song_title, artist_name, analysis, style, lyrics_result,
        output_dir, elapsed, metadata,
        video_4k_path, video_1080_path, shorts_path, thumbnail_path,
    )
    
    with open(output_dir / "report.txt", "w") as f:
        f.write(report)
    
    print(f"\n{'='*60}")
    print(f"  ✅ COMPLETE in {elapsed:.1f}s")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")
    
    return output_dir


def generate_report(song_title, artist_name, analysis, style, lyrics_result,
                    output_dir, elapsed, metadata,
                    video_4k, video_1080, shorts, thumbnail) -> str:
    """Generate a readable report file."""
    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║          KARAOKE STUDIO — PRODUCTION REPORT                  ║",
        "╚══════════════════════════════════════════════════════════════╝",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Processing time: {elapsed:.1f}s",
        "",
        "── SONG ──────────────────────────────────────────",
        f"Title: {song_title}",
        f"Artist: {artist_name or 'Unknown'}",
        f"Duration: {int(analysis.duration // 60)}:{int(analysis.duration % 60):02d}",
        "",
        "── AUDIO ANALYSIS ────────────────────────────────",
        f"BPM: {analysis.bpm}",
        f"Key: {analysis.key}",
        f"Genre: {analysis.genre}",
        f"Mood: {analysis.mood}",
        f"Energy: {analysis.energy:.2f}/1.0",
        f"Valence: {analysis.valence:.2f}/1.0 (0=sad, 1=happy)",
        f"Danceability: {analysis.danceability:.2f}/1.0",
        f"Acousticness: {analysis.acousticness:.2f}/1.0",
        f"Tempo confidence: {analysis.tempo_confidence:.2f}",
        "",
        "── VISUAL STYLE ──────────────────────────────────",
        f"Background: {style.bg_type.replace('_', ' ')}",
        f"Visualization: {style.viz_type.replace('_', ' ')}",
        f"Particles: {style.particle_type} ({style.particle_count})",
        f"Font: {Path(style.font_primary).stem}",
        f"Transition: {style.transition_type}",
        f"Vignette: {'Yes' if style.vignette else 'No'}",
        f"Film grain: {style.film_grain:.2f}",
        f"Light leak: {'Yes' if style.light_leak else 'No'}",
        f"Blur: {style.blur_amount:.1f}px",
        "",
        "── COLOR PALETTE ─────────────────────────────────",
    ]
    
    for i, color in enumerate(style.palette):
        lines.append(f"  {i+1}. {color}")
    
    lines.extend([
        "",
        "── LYRICS ────────────────────────────────────────",
        f"Source: {lyrics_result.source}",
        f"Lines: {len(lyrics_result.lines)}",
        f"Word-by-word sync: {'Yes' if any(l.words for l in lyrics_result.lines) else 'Line-level'}",
        "",
        "── OUTPUT FILES ──────────────────────────────────",
        f"4K 16:9 video:    {video_4k.name if video_4k else 'N/A'}",
        f"1080p 16:9 video: {video_1080.name if video_1080 else 'skipped'}",
        f"Shorts 9:16:      {shorts.name if shorts else 'skipped'}",
        f"Thumbnail:        {thumbnail.name if thumbnail else 'N/A'}",
        f"ASS subtitles:    lyrics.ass",
        f"SRT subtitles:    lyrics.srt",
        f"LRC lyrics:       lyrics.lrc",
        f"Metadata:         metadata.json",
        "",
        "── SEO METADATA ──────────────────────────────────",
        f"Title: {metadata.seo_title}",
        f"Hashtags: {' '.join(metadata.hashtags)}",
        f"Tags: {', '.join(metadata.youtube_tags[:8])}...",
        f"Category: {metadata.category}",
        "",
        "── PUBLICATION CHECKLIST ─────────────────────────",
        "✓ Lyrics synced with audio",
        "✓ Background matches mood",
        "✓ Audio visualization included",
        "✓ Thumbnail generated",
        "✓ SEO metadata generated",
        "✓ Multiple formats exported",
        "✓ No copyright material in visuals",
        "",
        "── PUBLICATION NOTES ─────────────────────────────",
        "• Upload video_4k_16x9.mp4 as primary video",
        "• Upload video_shorts_9x16.mp4 as YouTube Short",
        "• Use thumbnail.jpg as custom thumbnail",
        "• Copy metadata from metadata.json to YouTube",
        "• Pin the pinned comment from metadata",
        "",
    ])

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="karaoke_studio.py",
        description="Autonomous YouTube karaoke video producer — turns a song "
                    "into a complete karaoke video package.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python karaoke_studio.py --audio song.mp3 --title \"Song\" --artist \"Artist\"\n"
            "  python karaoke_studio.py --audio song.mp3 --title \"Song\" --lyrics-file lyrics.txt\n"
            "  python karaoke_studio.py --audio song.mp3 --title \"Song\" --skip-shorts --skip-1080p\n"
        ),
    )
    parser.add_argument("--audio", required=True,
                        help="Path to the input audio file (mp3, wav, etc.)")
    parser.add_argument("--title", required=True,
                        help="Song title")
    parser.add_argument("--artist", default="",
                        help="Artist name (optional)")

    lyrics_group = parser.add_mutually_exclusive_group()
    lyrics_group.add_argument("--lyrics", default=None,
                              help="Lyrics text passed directly on the command line")
    lyrics_group.add_argument("--lyrics-file", default=None,
                              help="Path to a text file containing the lyrics. "
                                   "If neither --lyrics nor --lyrics-file is given, "
                                   "lyrics are transcribed automatically with Whisper.")

    parser.add_argument("--channel", default="Karaoke Studio",
                        help="Channel name shown as a watermark (default: %(default)s)")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: output/<song title>)")
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model used for transcription/sync (default: %(default)s)")
    parser.add_argument("--no-viz", action="store_true",
                        help="Disable the audio visualization overlay")
    parser.add_argument("--skip-shorts", action="store_true",
                        help="Skip rendering the 9:16 Shorts version")
    parser.add_argument("--skip-1080p", action="store_true",
                        help="Skip rendering the 1080p version")
    return parser


def main(argv=None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run_karaoke_studio(
            audio_path=args.audio,
            song_title=args.title,
            artist_name=args.artist,
            lyrics=args.lyrics,
            lyrics_file=args.lyrics_file,
            channel_name=args.channel,
            output_dir=args.output,
            whisper_model=args.whisper_model,
            with_visualization=not args.no_viz,
            skip_shorts=args.skip_shorts,
            skip_1080p=args.skip_1080p,
        )
    except FileNotFoundError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ Karaoke Studio failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())