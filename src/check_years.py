import io
import gc
import time
import os
import random
import textwrap
import re
import qrcode
import requests
import numpy as np
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
import utils
import json
import logging

MIN_VALID_YEAR = 1500
MAX_VALID_YEAR = datetime.now().year + 1
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
json_file = os.path.join(OUTPUT_DIR, "hitster_cards", "songs.json")
new_json_file = os.path.join(OUTPUT_DIR, "hitster_cards", "songs_to_check.json")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='song_check.log', encoding='utf-8', level=logging.INFO)

def _validate_year(year: int | None) -> int | None:
    """Return year only if it falls in a plausible range, else None."""
    if year is None:
        return None
    if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
        return year
    return None

def get_year_from_musicbrainz(title, artist) -> int | None:
    q = f'recording:"{title}" AND artist:"{artist}"'
    params = {"query": q, "fmt": "json", "limit": 5}
    headers = {"User-Agent": "hitster-card-generator/2.0 (https://github.com/WhiteShunpo/hitster-cards-generator)"}
    try:
        r = requests.get("https://musicbrainz.org/ws/2/recording", params=params, headers=headers, timeout=10)
        if r.status_code in (429, 503):
            print("     Rate limit hit. Waiting 2 seconds before retrying...")
            time.sleep(2)
            r = requests.get("https://musicbrainz.org/ws/2/recording", params=params, headers=headers, timeout=10)
        r.raise_for_status()
        result_json = r.json()
        years = []
        if not result_json or "recordings" not in result_json:
            return None
        for rec in result_json.get("recordings", []):
            for rel in rec.get("releases", []) or []:
                date = rel.get("date")
                if date:
                    y = _validate_year(int(date.split("-")[0]))
                    if y is not None:
                        years.append(y)
        if not years:
            return None
        print(f"            MusicBrainz found years: {years} for '{title}' by '{artist}'")
        logger.info(f"MusicBrainz found years: {years} for '{title}' by '{artist}'")
        return min(years)
    except Exception:
        return None

def get_year_from_itunes(title, artist) -> int | None:
    q = urllib.parse.quote(f"{artist} {title}")
    url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=5"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        result_json = r.json()
        if not result_json or "results" not in result_json:
            return None
        years = []
        for res in result_json.get("results", []):
            rd = res.get("releaseDate")
            if rd:
                y = _validate_year(int(rd.split("-")[0]))
                if y is not None:
                    years.append(y)
        if not years:
            return None
        print(f"            iTunes found years: {years} for '{title}' by '{artist}'")
        logger.info(f"iTunes found years: {years} for '{title}' by '{artist}'")
        return min(years)
    except Exception:
        return None

def get_year_and_source(title, artist, orig_year) -> tuple[int | None, str | None]:
    """Get release year and source ('iTunes' or 'MusicBrainz') for a song.
    
    Args:
        title: Song title (first!)
        artist: Artist name (second!)
        orig_year: Fallback year from Spotify
    """
    itunes_year = get_year_from_itunes(title, artist)
    if itunes_year != orig_year and itunes_year is not None:
        return itunes_year, 'iTunes'
    
    # Rate-limit: MusicBrainz enforces ~1 req/sec
    time.sleep(1.1)
    musicbrainz_year = get_year_from_musicbrainz(title, artist)
    if musicbrainz_year != orig_year and musicbrainz_year is not None:
        return musicbrainz_year, 'MusicBrainz'
    
    return None, None


def check_songs_for_updated_years(json_file):
    songs = []
    songs_with_updated_years = []

    if os.path.exists(json_file):
        print(f"Loading local data from {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            songs = json.load(f)

        for i, song in enumerate(songs):
            try:
                title = song['name']
                artist = song['artist']
                orig_year = song['year']
                print(f"Checking song {i+1}/{len(songs)}: {title} by {artist} (Spotify year: {orig_year})")
                logger.info(f"Checking song {i+1}/{len(songs)}: {title} by {artist} (Spotify year: {orig_year})")
                new_year, source = get_year_and_source(title, artist, orig_year)
                if new_year is not None and new_year != orig_year:
                    print(f"  Found updated year: {new_year} (source: {source})")
                    logger.error(f"Found updated year: {new_year} (source: {source})")
                    song1 = {
                        'name': title,
                        'artist': artist,
                        'original_year': orig_year,
                        'new_year': new_year,
                        'year_source': source,                        
                    }
                    songs_with_updated_years.append(song1)
                else:
                    print("  No updated year found.")
                    logger.info(f"No updated year found for '{title}' by '{artist}'")
            except KeyboardInterrupt:
                return(songs_with_updated_years)
        return(songs_with_updated_years)

songs_to_check = check_songs_for_updated_years(json_file)
with open(new_json_file, 'w', encoding='utf-8') as f:
    json.dump(songs_to_check, f, indent=2)