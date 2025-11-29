import os
import sys
import re
import json
from fastmcp import FastMCP
from dotenv import load_dotenv
from langchain_perplexity import ChatPerplexity
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# --- UTILITY FUNCTIONS ---
def clean_perplexity_output(text: str) -> str:
    """
    Cleans Perplexity output by removing citation markers and normalizing whitespace.
    """
    if not text:
        return text
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\[\^\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Initialize MCP Server
mcp = FastMCP("MusicResearchBot")

# --- CLIENT CONFIGURATION ---

# 1. Perplexity Client
PPLX_API_KEY = os.getenv("PPLX_API_KEY")
if PPLX_API_KEY:
    pplx_client = ChatPerplexity(
        api_key=PPLX_API_KEY,
        model="sonar-reasoning", # Using reasoning model for higher quality
        temperature=0.2 # Lower temperature for more factual/precise results
    )
    PERPLEXITY_AVAILABLE = True
    print("[Server] Perplexity: ✓ Configured (Sonar Reasoning)", file=sys.stderr)
else:
    pplx_client = None
    PERPLEXITY_AVAILABLE = False
    print("[Server] Perplexity: ✗ Not configured", file=sys.stderr)

# 2. Spotify Client
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    
    spotify_client_id = os.getenv("SPOTIPY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    
    if spotify_client_id and spotify_client_secret and spotify_client_id != "your_client_id_here":
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=spotify_client_id,
            client_secret=spotify_client_secret
        ))
        SPOTIFY_AVAILABLE = True
        print("[Server] Spotify: ✓ Configured", file=sys.stderr)
    else:
        sp = None
        SPOTIFY_AVAILABLE = False
        print("[Server] Spotify: ✗ Not configured", file=sys.stderr)
except Exception as e:
    sp = None
    SPOTIFY_AVAILABLE = False
    print(f"[Server] Spotify initialization failed: {e}", file=sys.stderr)


# --- COMPLEX TOOLS ---

@mcp.tool
def analyze_musical_vibe_deep(description: str) -> str:
    """
    PERFORMS A DEEP PSYCHO-ACOUSTIC ANALYSIS of the user's request.
    Use this FIRST to deconstruct the user's abstract description into concrete musical parameters.
    
    Returns:
    - Key genres and sub-genres
    - Emotional landscape (valence, energy, arousal)
    - Sonic textures (e.g., "lo-fi", "distorted", "clean", "reverb-heavy")
    - Era/Decade references
    - Cultural context
    """
    print(f"[Tool] analyze_musical_vibe_deep called for: {description}", file=sys.stderr)
    if not PERPLEXITY_AVAILABLE: return "ERROR: Perplexity not configured"

    prompt = f"""
    You are a Musicologist and Psycho-acoustic Expert.
    
    USER REQUEST: "{description}"
    
    TASK: Deconstruct this request into a detailed musical profile. Do not list songs yet.
    Focus on the *feeling*, the *sound design*, and the *cultural context*.
    
    ANALYSIS REQUIRED:
    1. **Core Genres & Micro-genres**: Be specific (e.g., instead of "Rock", say "Shoegaze" or "Post-Punk Revival").
    2. **Sonic Texture**: Describe the production quality (e.g., "tape saturation", "crisp digital drums", "wall of sound").
    3. **Emotional Profile**: What is the precise mood? (e.g., "Melancholic but hopeful", "Aggressive and chaotic").
    4. **Rhythmic Feel**: BPM range, groove type (e.g., "swing", "four-on-the-floor", "syncopated").
    5. **Cultural Touchstones**: Associated scenes, eras, or movements.
    
    Provide a comprehensive analysis that will guide a curator to pick the PERFECT tracks.
    """
    try:
        response = pplx_client.invoke(prompt)
        return clean_perplexity_output(response.content)
    except Exception as e:
        return f"ERROR: {str(e)}"

@mcp.tool
def search_curated_tracklist(context: str, category: str = "mainstream") -> str:
    """
    Generates a HIGHLY CURATED list of tracks based on a deep musical context.
    
    Args:
        context: The deep analysis or vibe description.
        category: "mainstream" (well-known hits), "underground" (hidden gems), or "critics_choice" (highly rated).
    """
    print(f"[Tool] search_curated_tracklist ({category}) called", file=sys.stderr)
    if not PERPLEXITY_AVAILABLE: return "ERROR: Perplexity not configured"

    if category == "mainstream":
        focus = "Focus on defining hits, anthems, and widely recognized classics that perfectly fit the vibe."
    elif category == "underground":
        focus = "Focus on B-sides, deep cuts, indie releases, and overlooked gems. NO top 40 hits."
    else:
        focus = "Focus on critically acclaimed tracks, Pitchfork 'Best New Music', Rolling Stone classics, and tastemaker favorites."

    prompt = f"""
    You are a World-Class Music Curator.
    
    CONTEXT: {context}
    CATEGORY: {category.upper()}
    
    TASK: Curate a list of 10-15 songs that perfectly match the context.
    {focus}
    
    CRITERIA:
    - Cohesion: The songs must flow well together.
    - Relevance: Every song must be a 10/10 match for the vibe.
    - Variety: Avoid repeating the same artist more than once unless essential.
    
    OUTPUT FORMAT:
    - Title - Artist (Brief reason why it fits)
    """
    try:
        response = pplx_client.invoke(prompt)
        return clean_perplexity_output(response.content)
    except Exception as e:
        return f"ERROR: {str(e)}"

@mcp.tool
def search_lyrical_themes(theme: str, vibe_context: str) -> str:
    """
    Searches for songs specifically based on LYRICAL CONTENT and METAPHORS.
    Use this when the user mentions specific topics (e.g., "heartbreak", "summer nights", "rebellion").
    """
    print(f"[Tool] search_lyrical_themes called for: {theme}", file=sys.stderr)
    if not PERPLEXITY_AVAILABLE: return "ERROR: Perplexity not configured"

    prompt = f"""
    You are a Lyrical Analyst.
    
    THEME: "{theme}"
    VIBE CONTEXT: {vibe_context}
    
    TASK: Find 8-10 songs where the lyrics deeply explore this theme, while fitting the musical vibe.
    Look for specific metaphors, storytelling, and poetic connections.
    
    OUTPUT FORMAT:
    - Title - Artist (Key lyric snippet or thematic explanation)
    """
    try:
        response = pplx_client.invoke(prompt)
        return clean_perplexity_output(response.content)
    except Exception as e:
        return f"ERROR: {str(e)}"

@mcp.tool
def search_music_history_context(era_or_scene: str) -> str:
    """
    Provides historical context and seminal tracks for a specific era or scene.
    Useful for "80s Japanese City Pop" or "90s Seattle Grunge" requests.
    """
    print(f"[Tool] search_music_history_context called for: {era_or_scene}", file=sys.stderr)
    if not PERPLEXITY_AVAILABLE: return "ERROR: Perplexity not configured"

    prompt = f"""
    You are a Music Historian.
    
    TOPIC: {era_or_scene}
    
    TASK: Explain the defining characteristics of this era/scene and list 10 seminal tracks that defined it.
    Include both the massive hits that started it and the artistic peaks that defined its credibility.
    
    OUTPUT FORMAT:
    [Brief History/Context]
    
    Tracks:
    - Title - Artist
    """
    try:
        response = pplx_client.invoke(prompt)
        return clean_perplexity_output(response.content)
    except Exception as e:
        return f"ERROR: {str(e)}"

@mcp.tool
def get_spotify_audio_features_batch(track_names: str) -> str:
    """
    Searches for multiple tracks on Spotify and returns their detailed audio features (BPM, Key, Energy, etc.).
    Input: A string with multiple "Title - Artist" entries separated by newlines or commas.
    """
    print(f"[Tool] get_spotify_audio_features_batch called", file=sys.stderr)
    if not SPOTIFY_AVAILABLE: return "Spotify API not configured"

    tracks_data = []
    lines = [line.strip() for line in track_names.split('\n') if line.strip()]
    
    # Limit to first 5 for performance in this demo, but logic supports more
    for line in lines[:5]: 
        try:
            # Clean up line to get just Title - Artist
            clean_line = line.split('(')[0].strip() # Remove parenthetical comments
            
            results = sp.search(q=clean_line, limit=1, type="track")
            items = results['tracks']['items']
            if items:
                track = items[0]
                features = sp.audio_features([track['uri']])[0]
                
                if features:
                    info = (
                        f"✅ {track['name']} - {track['artists'][0]['name']}\n"
                        f"   BPM: {round(features['tempo'])} | Key: {features['key']} | "
                        f"Energy: {features['energy']:.2f} | Valence: {features['valence']:.2f} | "
                        f"Dance: {features['danceability']:.2f}"
                    )
                    tracks_data.append(info)
        except Exception as e:
            print(f"Error processing {line}: {e}", file=sys.stderr)
            continue
            
    if not tracks_data:
        return "No audio features found for these tracks."
        
    return "\n\n".join(tracks_data)

if __name__ == "__main__":
    print("\n" + "="*60, file=sys.stderr)
    print("[Server] Starting Complex MusicResearchBot MCP Server...", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)
    mcp.run()