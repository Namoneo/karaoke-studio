"""
Karaoke Lyrics System
Transcribes audio with Whisper, splits into karaoke lines, 
generates word-level and line-level synchronized ASS subtitles.
"""

import json
import re
import whisper
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
    """Sync user-provided lyrics to audio using Whisper for timing."""
    # Transcribe to get timing
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, word_timestamps=True, verbose=False)
    
    # Parse provided lyrics into lines
    provided_lines = [l.strip() for l in lyrics.strip().split("\n") if l.strip()]
    
    # Get Whisper segments for timing reference
    segments = result.get("segments", [])
    whisper_text = " ".join(seg["text"].strip() for seg in segments)
    whisper_words = []
    for seg in segments:
        for w in seg.get("words", []):
            whisper_words.append(w)
    
    # If no word timestamps, fall back to segment timing
    if not whisper_words:
        whisper_words = [{"word": seg["text"].strip(), "start": seg["start"], "end": seg["end"]} 
                        for seg in segments]
    
    # Match provided lines to Whisper segments by time proportion
    total_duration = segments[-1]["end"] if segments else 30.0
    
    lines = []
    num_lines = len(provided_lines)
    
    # Distribute time proportionally based on Whisper segment timing
    for i, text in enumerate(provided_lines):
        # Calculate proportional time window
        start_frac = i / num_lines
        end_frac = (i + 1) / num_lines
        
        start_time = total_duration * start_frac
        end_time = total_duration * end_frac
        
        # Try to align with Whisper segments
        for seg in segments:
            if seg["start"] <= start_time <= seg["end"]:
                start_time = seg["start"]
                break
        
        # Try to find word-level timing
        words = []
        words_in_line = text.split()
        line_duration = end_time - start_time
        word_duration = line_duration / max(len(words_in_line), 1)
        
        for j, word in enumerate(words_in_line):
            w_start = start_time + j * word_duration
            w_end = start_time + (j + 1) * word_duration
            words.append({"word": word, "start": w_start, "end": w_end})
        
        lines.append(LyricLine(
            text=text,
            start=start_time,
            end=end_time,
            words=words,
        ))
    
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