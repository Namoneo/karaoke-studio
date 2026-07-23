"""
Karaoke Lyrics System
Transcribes audio with Whisper, splits into karaoke lines, 
generates word-level and line-level synchronized ASS subtitles.
"""

import json
import re
import difflib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class LyricLine:
    """A single karaoke line."""
    text: str
    start: float    # seconds
    end: float      # seconds
    words: list     # list of {word, start, end}


@dataclass 
class LyricsResult:
    """Complete lyrics with timing."""
    lines: List[LyricLine]
    full_text: str
    lrc_content: str
    srt_content: str
    ass_content: str
    source: str      # "user" or "whisper"


def process_lyrics(audio_path: str, lyrics: Optional[str] = None,
                   style_config: dict = None,
                   model_name: str = "base") -> LyricsResult:
    """
    Process lyrics: if provided, sync to audio; if not, transcribe with Whisper.
    Returns ASS, SRT, and LRC formats.
    """
    audio_path = str(audio_path)

    if lyrics and lyrics.strip():
        # User provided lyrics — try to sync with Whisper timestamps
        lines = sync_provided_lyrics(audio_path, lyrics, model_name=model_name)
        source = "user"
    else:
        # Transcribe with Whisper
        lines = transcribe_with_whisper(audio_path, model_name=model_name)
        source = "whisper"
    
    # Generate subtitle formats
    full_text = "\n".join(l.text for l in lines)
    lrc_content = generate_lrc(lines)
    srt_content = generate_srt(lines)
    ass_content = generate_ass(lines, style_config or {})
    
    return LyricsResult(
        lines=lines,
        full_text=full_text,
        lrc_content=lrc_content,
        srt_content=srt_content,
        ass_content=ass_content,
        source=source,
    )


def transcribe_with_whisper(audio_path: str, model_name: str = "base") -> List[LyricLine]:
    """Transcribe audio with Whisper and create karaoke lines."""
    import whisper
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, word_timestamps=True, verbose=False)
    
    lines = []
    current_line_words = []
    current_line_start = 0
    
    segments = result.get("segments", [])
    
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # No word-level timing — use segment timing
            lines.append(LyricLine(
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                words=[{"word": seg["text"].strip(), "start": seg["start"], "end": seg["end"]}]
            ))
            continue
        
        # Group words into lines (max ~7 words per line, or on punctuation)
        for w in words:
            word_text = w["word"].strip()
            if not word_text:
                continue
            
            if not current_line_words:
                current_line_start = w["start"]
            
            current_line_words.append({
                "word": word_text,
                "start": w["start"],
                "end": w["end"],
            })
            
            # Check if we should break the line
            should_break = False
            if len(current_line_words) >= 7:
                should_break = True
            elif word_text.endswith(('.', '!', '?', ',', ';')):
                if len(current_line_words) >= 3:
                    should_break = True
            
            if should_break:
                line_text = " ".join(w["word"] for w in current_line_words)
                lines.append(LyricLine(
                    text=line_text,
                    start=current_line_start,
                    end=current_line_words[-1]["end"],
                    words=current_line_words,
                ))
                current_line_words = []
    
    # Don't forget last line
    if current_line_words:
        line_text = " ".join(w["word"] for w in current_line_words)
        lines.append(LyricLine(
            text=line_text,
            start=current_line_start,
            end=current_line_words[-1]["end"],
            words=current_line_words,
        ))
    
    return lines


def sync_provided_lyrics(audio_path: str, lyrics: str,
                         model_name: str = "base") -> List[LyricLine]:
    """Sync user-provided lyrics to audio via forced alignment.

    Whisper transcribes the audio to get word-level timestamps, then the
    user's lyrics are aligned to that recognized word stream: words Whisper
    heard receive their real timestamps, and any words in between are
    interpolated across the surrounding anchors. This keeps the correct
    (user-supplied) spelling while getting timing from the audio — far more
    accurate than distributing lines evenly over the duration.
    """
    import whisper
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, word_timestamps=True, verbose=False)

    provided_lines = [l.strip() for l in lyrics.strip().split("\n") if l.strip()]
    if not provided_lines:
        return []

    segments = result.get("segments", [])

    # Flatten Whisper's recognized words with their timestamps.
    whisper_words = []
    for seg in segments:
        for w in seg.get("words", []):
            wt = str(w.get("word", "")).strip()
            if wt:
                whisper_words.append({
                    "word": wt,
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                })
    # If there are no word-level timestamps, fall back to segment-level timing.
    if not whisper_words:
        for seg in segments:
            for tok in str(seg.get("text", "")).split():
                whisper_words.append({
                    "word": tok,
                    "start": float(seg["start"]),
                    "end": float(seg["end"]),
                })

    total_duration = float(segments[-1]["end"]) if segments else 30.0

    # Nothing to align against — fall back to even distribution.
    if not whisper_words:
        return _proportional_lines(provided_lines, total_duration)

    # Build a flat list of the user's word tokens, remembering which line each
    # belongs to so we can regroup after timing them.
    tokens = []
    for li, line_text in enumerate(provided_lines):
        for word in line_text.split():
            tokens.append({"word": word, "line": li, "start": None, "end": None})

    prov_norm = [_normalize_token(t["word"]) for t in tokens]
    whis_norm = [_normalize_token(w["word"]) for w in whisper_words]

    # Anchor matching provided words to recognized words in sequence order.
    matcher = difflib.SequenceMatcher(a=prov_norm, b=whis_norm, autojunk=False)
    matched = 0
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            a_idx = block.a + k
            b_idx = block.b + k
            if not prov_norm[a_idx]:  # skip empty (punctuation-only) tokens
                continue
            tokens[a_idx]["start"] = whisper_words[b_idx]["start"]
            tokens[a_idx]["end"] = whisper_words[b_idx]["end"]
            matched += 1

    # Too few anchors to trust the alignment — fall back to even distribution.
    if matched < max(1, int(len(tokens) * 0.15)):
        return _proportional_lines(provided_lines, total_duration)

    _interpolate_unmatched(tokens, total_duration)

    # Regroup timed tokens back into their original lines.
    lines = []
    for li, line_text in enumerate(provided_lines):
        line_tokens = [t for t in tokens if t["line"] == li]
        if not line_tokens:
            continue
        words = []
        for t in line_tokens:
            start = float(t["start"])
            end = max(float(t["end"]), start + 0.05)
            words.append({"word": t["word"], "start": round(start, 3), "end": round(end, 3)})
        line_start = words[0]["start"]
        line_end = max(words[-1]["end"], line_start + 0.3)
        lines.append(LyricLine(text=line_text, start=line_start, end=line_end, words=words))

    return lines


def _normalize_token(token: str) -> str:
    """Lowercase a word and drop punctuation for alignment comparisons."""
    return "".join(ch for ch in token.strip().lower() if ch.isalnum())


def _interpolate_unmatched(tokens: list, total_duration: float) -> None:
    """Fill in start/end for tokens Whisper did not anchor, in place.

    Unmatched runs are spread evenly between the timestamps of the nearest
    anchored words on either side (or the clip boundaries at the edges).
    """
    n = len(tokens)
    if n == 0:
        return

    anchors = [i for i, t in enumerate(tokens) if t["start"] is not None]

    # No anchors survived — spread everything evenly over the duration.
    if not anchors:
        step = total_duration / n
        for i, t in enumerate(tokens):
            t["start"] = i * step
            t["end"] = (i + 1) * step
        return

    # Leading run before the first anchor: spread over [0, first_start).
    first = anchors[0]
    if first > 0:
        end_t = tokens[first]["start"]
        step = end_t / first
        for i in range(first):
            tokens[i]["start"] = i * step
            tokens[i]["end"] = (i + 1) * step

    # Interior runs between consecutive anchors.
    for a, b in zip(anchors, anchors[1:]):
        gap = b - a - 1
        if gap <= 0:
            continue
        t0 = tokens[a]["end"]
        t1 = tokens[b]["start"]
        step = max(0.0, t1 - t0) / gap
        for j in range(1, gap + 1):
            idx = a + j
            tokens[idx]["start"] = t0 + (j - 1) * step
            tokens[idx]["end"] = t0 + j * step

    # Trailing run after the last anchor: spread over (last_end, total_duration].
    last = anchors[-1]
    trailing = n - 1 - last
    if trailing > 0:
        t0 = tokens[last]["end"]
        t1 = max(total_duration, t0 + trailing * 0.3)
        step = (t1 - t0) / trailing
        for j in range(1, trailing + 1):
            idx = last + j
            tokens[idx]["start"] = t0 + (j - 1) * step
            tokens[idx]["end"] = t0 + j * step


def _proportional_lines(provided_lines: List[str], total_duration: float) -> List[LyricLine]:
    """Fallback: distribute lines evenly across the duration when alignment
    is not possible (no usable Whisper timing or too few matched words)."""
    lines = []
    num_lines = max(len(provided_lines), 1)
    for i, text in enumerate(provided_lines):
        start_time = total_duration * (i / num_lines)
        end_time = total_duration * ((i + 1) / num_lines)
        words_in_line = text.split()
        word_duration = (end_time - start_time) / max(len(words_in_line), 1)
        words = []
        for j, word in enumerate(words_in_line):
            words.append({
                "word": word,
                "start": round(start_time + j * word_duration, 3),
                "end": round(start_time + (j + 1) * word_duration, 3),
            })
        lines.append(LyricLine(text=text, start=round(start_time, 3),
                               end=round(end_time, 3), words=words))
    return lines


def generate_lrc(lines: List[LyricLine]) -> str:
    """Generate LRC format lyrics file."""
    lrc_lines = []
    for line in lines:
        minutes = int(line.start // 60)
        seconds = line.start % 60
        lrc_lines.append(f"[{minutes:02d}:{seconds:05.2f}]{line.text}")
    return "\n".join(lrc_lines)


def generate_srt(lines: List[LyricLine]) -> str:
    """Generate SRT subtitle file."""
    srt_lines = []
    for i, line in enumerate(lines, 1):
        start_ts = format_srt_time(line.start)
        end_ts = format_srt_time(line.end)
        srt_lines.append(f"{i}\n{start_ts} --> {end_ts}\n{line.text}\n")
    return "\n".join(srt_lines)


def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_ass_time(seconds: float) -> str:
    """Format seconds as ASS timestamp."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass(lines: List[LyricLine], style_config: dict) -> str:
    """Generate ASS subtitle file with word-by-word karaoke highlighting."""
    font_name = style_config.get("font_name", "Helvetica Neue")
    font_size = style_config.get("font_size", 56)
    font_color = style_config.get("font_color", "#FFFFFF")
    outline_color = style_config.get("outline_color", "#000000")
    highlight_color = style_config.get("highlight_color", "#FFD700")
    transition_type = style_config.get("transition_type", "dissolve")
    
    # Convert hex colors to ASS format (&HAABBGGRR)
    def hex_to_ass(h):
        h = h.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"&H00{b:02X}{g:02X}{r:02X}"
    
    primary_color = hex_to_ass(font_color)
    outline_c = hex_to_ass(outline_color)
    highlight_c = hex_to_ass(highlight_color)
    
    # Build ASS header
    header = f"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{highlight_c},{outline_c},&H80000000,0,0,0,0,100,100,0,0,1,3,2,2,120,120,80,1
Style: Highlight,{font_name},{font_size},{highlight_c},{primary_color},{outline_c},&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,120,120,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    for line in lines:
        start = format_ass_time(line.start)
        end = format_ass_time(line.end)
        
        # Build karaoke line with \k timing (word-by-word)
        if line.words and len(line.words) > 1:
            karaoke_parts = []
            for w in line.words:
                word_duration = max(1, int((w["end"] - w["start"]) * 100))
                # Clean word
                clean_word = w["word"].replace("{", "").replace("}", "").replace("\\", "")
                karaoke_parts.append(f"{{\\k{word_duration}}}{clean_word}")
            text = "".join(karaoke_parts)
        else:
            text = line.text.replace("{", "").replace("}", "")
            total_duration = max(1, int((line.end - line.start) * 100))
            text = f"{{\\k{total_duration}}}{text}"
        
        # Add transition effect
        if transition_type == "fade" or transition_type == "dissolve":
            text = f"{{\\fad(300,200)}}{text}"
        elif transition_type == "slide_fade":
            # Quick fade in/out (a true positional slide needs absolute
            # coordinates, which vary with resolution — a snappy fade is the
            # resolution-independent equivalent).
            text = f"{{\\fad(200,150)}}{text}"
        elif transition_type == "zoom_in":
            text = f"{{\\fad(200,150)\\fscx0\\fscy0\\t(0,300,\\fscx100\\fscy100)}}{text}"
        elif transition_type == "soft_grow":
            text = f"{{\\fad(400,300)\\fscx80\\fscy80\\t(0,500,\\fscx100\\fscy100)}}{text}"
        elif transition_type == "pop_in":
            text = f"{{\\fad(100,100)\\fscx0\\fscy0\\t(0,200,\\fscx115\\fscy115)\\t(200,300,\\fscx100\\fscy100)}}{text}"
        elif transition_type == "slow_fade":
            text = f"{{\\fad(600,400)}}{text}"
        elif transition_type == "gentle_fade":
            text = f"{{\\fad(400,300)}}{text}"
        else:
            text = f"{{\\fad(300,200)}}{text}"
        
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    
    return header + "\n".join(events) + "\n"