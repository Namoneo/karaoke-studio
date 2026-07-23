# 🎤 Karaoke Studio

**Autonomous YouTube Karaoke Video Producer**

Transform any song into a complete, professional karaoke video package with minimal interaction.

## Features

- **Audio Analysis** — Auto-detects BPM, key, mood, energy, genre via librosa
- **Visual Style Engine** — Every song gets a unique visual identity (28 background types, mood-matched palettes, fonts, particles)
- **Animated Backgrounds** — 28 procedural backgrounds rendered natively at the target resolution (up to 4K) as short **seamless loops** the compositor tiles to length
- **Karaoke Lyrics** — Whisper transcription with word-by-word sync; user-supplied lyrics are **force-aligned** to the audio. ASS/SRT/LRC output
- **Audio Visualization** — Distinct reactive styles: circular scope (avectorscope), frequency bars (showfreqs), waveform and minimal line (showwaves)
- **Branding** — Title card, channel watermark, optional logo overlay, animated Subscribe call-to-action
- **Multi-format Export** — 4K 16:9, 1080p, 9:16 Shorts, thumbnail
- **SEO Metadata** — Title, description, tags, hashtags, pinned comment
- **Measured Quality Checks** — The report verifies real lyric timing and output files, not a fixed checklist

## Requirements

- Python 3.12+
- ffmpeg (with drawtext, libass, libfreetype)
- macOS, Linux, or Windows — fonts are auto-detected per platform, falling
  back to matplotlib's bundled DejaVuSans if no system fonts are found

## Installation

### macOS

```bash
brew install python@3.12 ffmpeg

git clone https://github.com/Namoneo/karaoke-studio.git
cd karaoke-studio
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Linux (Debian/Ubuntu)

```bash
sudo apt install python3 python3-venv ffmpeg fonts-liberation fonts-dejavu

git clone https://github.com/Namoneo/karaoke-studio.git
cd karaoke-studio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# With provided lyrics
python karaoke_studio.py   --audio song.mp3   --title "Song Name"   --artist "Artist Name"   --lyrics-file lyrics.txt   --channel "Your Channel"

# Auto-transcribe (no lyrics provided)
python karaoke_studio.py   --audio song.mp3   --title "Song Name"   --artist "Artist Name"

# Skip Shorts or 1080p for faster processing
python karaoke_studio.py --audio song.mp3 --title "Song" --skip-shorts --skip-1080p

# Add a channel logo and disable the Subscribe call-to-action
python karaoke_studio.py --audio song.mp3 --title "Song" --logo logo.png --no-subscribe
```

Other flags: `--whisper-model {tiny,base,small,medium,large}`, `--no-viz`, `--output DIR`.

## Output

```
output/Song_Name/
├── video_4k_16x9.mp4      # 4K 16:9 YouTube video
├── video_1080p_16x9.mp4   # 1080p version
├── video_shorts_9x16.mp4  # 9:16 Shorts version
├── thumbnail.jpg          # YouTube thumbnail
├── lyrics.ass              # ASS karaoke subtitles (word-by-word)
├── lyrics.srt              # SRT subtitles
├── lyrics.lrc              # LRC lyrics file
├── metadata.json           # SEO metadata
├── analysis.json           # Audio analysis data
├── style.json              # Visual style data
└── report.txt              # Production report
```

## Mood-Based Visual Styles

| Mood | Background | Visualization | Font |
|------|-----------|---------------|------|
| Dance | Neon grid, pulses | Circular spectrum | Bold Sans |
| Romantic | Golden particles, bokeh | Minimal spectrum | Elegant Serif |
| Sad | Rain, fog, clouds | Minimal waveform | Elegant Serif |
| Lo-fi | City lights, night sky | Minimal spectrum | Rounded |
| Epic | Space nebula, aurora | Circular spectrum | Elegant Serif |
| Acoustic | Floating dust, sunrise | Minimal spectrum | Rounded |
| Happy | Bubbles, sunburst | Circular spectrum | Modern Sans |

## Architecture

```
src/
├── audio/analyzer.py          # librosa analysis
├── visual/style_engine.py     # mood → style mapping
├── visual/background_gen.py   # 28 procedural backgrounds
├── lyrics/karaoke.py          # Whisper + ASS generation
├── export/composer.py         # ffmpeg composition
└── metadata/seo_generator.py  # YouTube SEO
```

## License

MIT
