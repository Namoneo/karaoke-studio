"""
SEO Metadata Generator
Generates YouTube-optimized metadata: title, description, tags, hashtags, pinned comment.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class VideoMetadata:
    """YouTube SEO metadata."""
    seo_title: str
    seo_description: str
    hashtags: List[str]
    keywords: List[str]
    youtube_tags: List[str]
    thumbnail_title: str
    short_description: str
    pinned_comment: str
    category: str


mood_descriptions = {
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


def generate_metadata(
    song_title: str,
    artist_name: str,
    mood: str,
    genre: str,
    bpm: float,
    duration: float,
    has_lyrics: bool = True,
    channel_name: str = "",
) -> VideoMetadata:
    """Generate complete YouTube SEO metadata."""
    
    title_clean = song_title.strip()
    artist_clean = artist_name.strip() if artist_name else ""
    
    # === SEO Title ===
    title_options = [
        f"{title_clean} - {artist_clean} | Karaoke Version" if artist_clean else f"{title_clean} | Karaoke Version",
        f"{title_clean} ({artist_clean}) Karaoke - Sing Along!" if artist_clean else f"{title_clean} Karaoke - Sing Along!",
        f"{title_clean} Karaoke | {mood.title()} Vibes" + (f" | {artist_clean}" if artist_clean else ""),
    ]
    seo_title = title_options[0]
    # Keep under 100 chars
    if len(seo_title) > 100:
        seo_title = seo_title[:97] + "..."
    
    # === Description ===
    mood_desc = mood_descriptions.get(mood, "a beautiful atmosphere")
    
    desc_lines = [
        f"🎵 {title_clean}" + (f" - {artist_clean}" if artist_clean else ""),
        f"🎤 Karaoke Version — Sing Along!",
        "",
        f"Immerse yourself in {mood_desc} with this stunning karaoke experience.",
        f"Perfect for singing alone, with friends, or recording your own cover.",
        "",
        f"⏱️ Duration: {int(duration // 60)}:{int(duration % 60):02d}",
        f"🎼 Key: {genre}",
        f"💃 Tempo: {bpm:.0f} BPM",
        f"🎨 Mood: {mood.title()}",
        "",
        "📸 Features:",
        "✓ Word-by-word lyrics synchronization",
        "✓ 4K Ultra HD background animation",
        "✓ Audio visualization",
        "✓ Mobile & TV friendly",
        "",
        "🔔 Don't forget to LIKE, SUBSCRIBE, and hit the bell for more karaoke videos!",
        "",
        "💬 Request a song in the comments below!",
        "",
        "⚠️ This video is for entertainment purposes only.",
        "No copyright infringement intended.",
    ]
    
    seo_description = "\n".join(desc_lines)
    
    # === Hashtags ===
    mood_tags = {
        "dance": ["#dancekaraoke", "#dancemusic", "#partykaraoke"],
        "happy": ["#happysongs", "#feelgoodkaraoke", "#upbeat"],
        "sad": ["#sadkaraoke", "#emotional", "#feelingsongs"],
        "melancholic": ["#melancholic", "#emotionalkaraoke", "#deepvibes"],
        "acoustic": ["#acoustickaraoke", "#acousticmusic", "#unplugged"],
        "lofi": ["#lofikaraoke", "#lofi", "#chillvibes"],
        "romantic": ["#romantickaraoke", "#lovesongs", "#romanticmusic"],
        "epic": ["#epickaraoke", "#cinematic", "#epicmusic"],
        "ambient": ["#ambientkaraoke", "#relaxing", "#ambientmusic"],
        "warm": ["#warmkaraoke", "#cozyvibes", "#warmmusic"],
        "energetic": ["#energetickaraoke", "#highenergy", "#powerful"],
        "chill": ["#chillkaraoke", "#chillvibes", "#relaxingmusic"],
    }
    
    base_hashtags = ["#karaoke", "#singalong", "#karaokesong", "#karaokeversion"]
    mood_hashtags = mood_tags.get(mood, ["#karaoke"])
    if artist_clean:
        artist_tag = "#" + artist_clean.replace(" ", "").replace("&", "and")
        mood_hashtags = [artist_tag] + mood_hashtags
    song_tag = "#" + title_clean.replace(" ", "").replace("&", "and")[:30]
    
    hashtags = base_hashtags + mood_hashtags + [song_tag]
    
    # === Keywords ===
    keywords = [
        song_title.lower(),
        f"{song_title} karaoke".lower(),
        f"{song_title} karaoke version".lower(),
        f"{song_title} sing along".lower(),
    ]
    if artist_clean:
        keywords.extend([
            f"{artist_clean} karaoke".lower(),
            f"{artist_clean} {song_title} karaoke".lower(),
            artist_clean.lower(),
            f"{artist_clean} songs".lower(),
        ])
    keywords.extend([
        "karaoke", "sing along", "karaoke version", "karaoke songs",
        mood, f"{mood} karaoke", f"{mood} music",
        genre.lower(), f"{genre} karaoke",
        "karaoke with lyrics", "karaoke 4k",
    ])
    
    # === YouTube Tags ===
    youtube_tags = list(set(keywords))[:500 // 10]  # Keep under 500 chars
    
    # === Thumbnail Title ===
    thumbnail_title = f"{title_clean} Karaoke"
    if artist_clean:
        thumbnail_title += f" - {artist_clean}"
    
    # === Short Description ===
    short_description = f"{title_clean} Karaoke"
    if artist_clean:
        short_description += f" by {artist_clean}"
    short_description += f" | {mood.title()} vibes | Sing along with synced lyrics!"
    
    # === Pinned Comment ===
    pinned_comment = (
        f"🎵 Thank you for watching! If you enjoyed this karaoke video, "
        f"please LIKE and SUBSCRIBE for more! 🎤✨\n\n"
        f"What song should I make next? Drop your requests below! 👇"
    )
    
    # === Category ===
    category = "Music"
    
    return VideoMetadata(
        seo_title=seo_title,
        seo_description=seo_description,
        hashtags=hashtags,
        keywords=keywords,
        youtube_tags=youtube_tags,
        thumbnail_title=thumbnail_title,
        short_description=short_description,
        pinned_comment=pinned_comment,
        category=category,
    )