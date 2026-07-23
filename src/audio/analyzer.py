"""
Audio Analysis Module
Analyzes song for BPM, key, energy, mood, genre classification.
Uses librosa for acoustic features and whisper for lyrics transcription.
"""

import json
import numpy as np
import librosa
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class AudioAnalysis:
    """Complete analysis of a song's acoustic properties."""
    duration: float          # seconds
    bpm: float               # beats per minute
    key: str                 # musical key (e.g. "C major")
    energy: float            # 0.0-1.0 overall energy
    danceability: float      # 0.0-1.0
    acousticness: float      # 0.0-1.0
    valence: float           # 0.0-1.0 (sad → happy)
    mood: str                # primary mood label
    moods: list              # all matching mood labels
    color_palette: list      # hex colors
    genre: str               # detected genre
    spectral_centroid: float # brightness
    rms_mean: float          # loudness
    rms_std: float           # dynamic range
    tempo_confidence: float  # tempo detection confidence
    beat_times: list         # beat positions in seconds
    sections: list           # song structure sections


def analyze_audio(audio_path: str) -> AudioAnalysis:
    """Full analysis pipeline using librosa."""
    audio_path = str(audio_path)
    
    # Load audio
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    
    # Tempo and beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    
    # BPM — tempo can be a numpy array in newer librosa
    bpm = float(np.atleast_1d(tempo)[0])
    
    # Key detection
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    key = detect_key(chroma)
    
    # Spectral features
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_centroid_mean = float(np.mean(spectral_centroids))
    
    # RMS energy
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = float(np.mean(rms))
    rms_std = float(np.std(rms))
    
    # Energy score (0-1)
    energy = min(1.0, rms_mean * 8.0)
    
    # Danceability — based on tempo regularity and beat strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_std = float(np.std(onset_env))
    onset_mean = float(np.mean(onset_env))
    danceability = min(1.0, (onset_mean / (onset_std + 1e-6)) * 0.5)
    # Also factor in BPM
    if 80 <= bpm <= 150:
        danceability = min(1.0, danceability * 1.3)
    
    # Acousticness — spectral flatness
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    acousticness = float(np.mean(flatness))
    # Lower flatness = more tonal/harmonic = more acoustic
    acousticness = 1.0 - min(1.0, acousticness * 3.0)
    
    # Valence (mood brightness) — based on key (major=happy, minor=sad) + spectral brightness
    is_major = "major" in key.lower()
    brightness = min(1.0, spectral_centroid_mean / 4000.0)
    valence = (0.5 + (0.3 if is_major else -0.2) + brightness * 0.4)
    valence = max(0.0, min(1.0, valence))
    
    # Mood classification
    moods = classify_mood(energy, valence, bpm, acousticness, spectral_centroid_mean)
    primary_mood = moods[0]
    
    # Color palette
    color_palette = get_mood_colors(primary_mood, valence, energy)
    
    # Genre estimation
    genre = estimate_genre(bpm, energy, acousticness, danceability, valence, spectral_centroid_mean)
    
    # Song sections (approximate)
    sections = detect_sections(y, sr, beat_times)
    
    # Tempo confidence
    tempo_confidence = float(np.std(librosa.feature.tempo(y=y, sr=sr)))
    tempo_confidence = max(0.0, 1.0 - tempo_confidence)
    
    return AudioAnalysis(
        duration=duration,
        bpm=round(bpm, 1),
        key=key,
        energy=round(energy, 3),
        danceability=round(danceability, 3),
        acousticness=round(acousticness, 3),
        valence=round(valence, 3),
        mood=primary_mood,
        moods=moods,
        color_palette=color_palette,
        genre=genre,
        spectral_centroid=round(spectral_centroid_mean, 1),
        rms_mean=round(rms_mean, 4),
        rms_std=round(rms_std, 4),
        tempo_confidence=round(tempo_confidence, 3),
        beat_times=[round(t, 3) for t in beat_times],
        sections=sections,
    )


def detect_key(chroma):
    """Detect musical key from chroma features."""
    # Average chroma across time
    chroma_mean = np.mean(chroma, axis=1)
    
    # Pitch classes
    pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Major and minor profiles (Krumhansl-Schmuckler)
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    best_key = "C major"
    best_corr = -1
    
    for i in range(12):
        rotated = np.roll(chroma_mean, i)
        major_corr = np.corrcoef(rotated, major_profile)[0, 1]
        minor_corr = np.corrcoef(rotated, minor_profile)[0, 1]
        
        if major_corr > best_corr:
            best_corr = major_corr
            best_key = f"{pitch_names[i]} major"
        if minor_corr > best_corr:
            best_corr = minor_corr
            best_key = f"{pitch_names[i]} minor"
    
    return best_key


def classify_mood(energy, valence, bpm, acousticness, spectral_centroid):
    """Classify song into mood categories."""
    moods = []
    
    # High energy + high valence = dance/happy
    if energy > 0.6 and valence > 0.5:
        if bpm > 120:
            moods.append("dance")
        else:
            moods.append("happy")
    
    # Low valence = sad/melancholic
    if valence < 0.35:
        if energy < 0.4:
            moods.append("sad")
        else:
            moods.append("melancholic")
    
    # High acousticness + low energy = relaxing/acoustic
    if acousticness > 0.5 and energy < 0.4:
        moods.append("acoustic")
    
    # Low BPM + low energy = chill/lo-fi
    if bpm < 90 and energy < 0.4:
        moods.append("lofi")
    
    # Romantic — moderate energy, positive valence, acoustic
    if 0.3 < energy < 0.6 and valence > 0.4 and acousticness > 0.3:
        moods.append("romantic")
    
    # Epic — high energy, low valence, high spectral centroid
    if energy > 0.5 and spectral_centroid > 2500:
        moods.append("epic")
    
    # Ambient — very low energy
    if energy < 0.2:
        moods.append("ambient")
    
    # Warm — moderate everything, positive valence
    if valence > 0.5 and 0.3 < energy < 0.6:
        moods.append("warm")
    
    # Fallback
    if not moods:
        if energy > 0.5:
            moods.append("energetic")
        elif valence > 0.5:
            moods.append("warm")
        else:
            moods.append("chill")
    
    return moods


def get_mood_colors(mood, valence, energy):
    """Get color palette based on mood."""
    palettes = {
        "dance": ["#FF006E", "#FB5607", "#FFBE0B", "#8338EC", "#3A86FF"],
        "happy": ["#FFD60A", "#FF9500", "#FF2D55", "#34C759", "#5AC8FA"],
        "sad": ["#1E3A5F", "#2C5F8A", "#4A90B8", "#7BA9C9", "#A8C8DD"],
        "melancholic": ["#2D3142", "#4F5D75", "#8B9DAB", "#C0C8CC", "#E8E8E8"],
        "acoustic": ["#D4A574", "#C49B6C", "#8B7355", "#6B5D4F", "#A89060"],
        "lofi": ["#7E5A9B", "#5D4E6D", "#3D3450", "#2A2535", "#1A1520"],
        "romantic": ["#FF6B9D", "#C44569", "#F8B195", "#F67280", "#E55475"],
        "epic": ["#0A0E27", "#1A1A40", "#3D2C8D", "#916BBF", "#C996CC"],
        "ambient": ["#0D1B2A", "#1B263B", "#415A77", "#778DA9", "#E0E1DD"],
        "warm": ["#FF9F1C", "#FFBF69", "#FFD8A0", "#CB997E", "#A0522D"],
        "energetic": ["#FF4500", "#FF6347", "#FFD700", "#FF8C00", "#FF1493"],
        "chill": ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"],
    }
    
    return palettes.get(mood, palettes["chill"])


def estimate_genre(bpm, energy, acousticness, danceability, valence, spectral_centroid):
    """Estimate genre from acoustic features."""
    if bpm < 70 and energy < 0.3:
        return "Ambient"
    if bpm < 90 and energy < 0.4 and acousticness > 0.4:
        return "Lo-fi"
    if bpm > 120 and energy > 0.6 and danceability > 0.5:
        return "Dance/EDM"
    if acousticness > 0.6 and energy < 0.5:
        return "Acoustic"
    if energy > 0.5 and valence < 0.4:
        return "Rock/Alternative"
    if energy > 0.6 and valence > 0.5:
        return "Pop"
    if bpm > 100 and danceability > 0.4:
        return "Pop"
    return "Indie"


def detect_sections(y, sr, beat_times):
    """Detect song structure sections (intro, verse, chorus, etc.)."""
    # Use structural segmentation via self-similarity
    try:
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        # Simplify: just divide into rough sections
        duration = len(y) / sr
        num_sections = max(4, min(10, int(duration / 30)))
        section_length = duration / num_sections
        
        sections = []
        for i in range(num_sections):
            start = i * section_length
            # Label sections based on position
            if i == 0:
                label = "intro"
            elif i == num_sections - 1:
                label = "outro"
            elif i == num_sections // 2:
                label = "chorus"
            elif i % 2 == 1:
                label = "verse"
            else:
                label = "bridge"
            sections.append({"start": round(start, 1), "label": label})
        return sections
    except Exception:
        return [{"start": 0, "label": "full"}]