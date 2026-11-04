#!/usr/bin/env python3

"""
Hitster Card Generator
Generate custom Hitster-style music game cards from Spotify playlists.
"""

import os
import json
import argparse
from dotenv import load_dotenv
import utils

# =============================================================================
# CONFIGURATION
# =============================================================================

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
# Step UP one level to reach the project root
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Correct paths relative to Project Root
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
FONT_DIR = os.path.join(PROJECT_ROOT, "fonts")
LINKS_FILE = os.path.join(PROJECT_ROOT, "links.txt")

FONT_PATHS = {
    'year': os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
    'artist': os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf"),
    'song': os.path.join(FONT_DIR, "Montserrat-MediumItalic.ttf")
}
# Color gradient for year-based card colors (oldest to newest)
COLOR_GRADIENT = [
    "#7030A0",  # Purple (oldest)
    "#E31C79",  # Pink
    "#FF6B9D",  # Light pink
    "#FFA500",  # Orange
    "#FFD700",  # Gold
    "#87CEEB",  # Sky blue
    "#4169E1",  # Royal blue (newest)
]

# Card design parameters
CARD_SIZE = 2000  # pixels
NEON_COLORS = [(255, 0, 100), (0, 200, 255), (0, 255, 120), (255, 255, 0)]

db = {"fonts_dict": FONT_PATHS, 
      "color_gradient": COLOR_GRADIENT,
      "card_size": CARD_SIZE,
      "neon_colors": NEON_COLORS}
utils.db = db 

# =============================================================================
# FINAL INTEGRATED PIPELINE
# =============================================================================

def generate_hitster_cards(db, playlist_url=None, client_id=None, client_secret=None, output_dir="hitster_cards", fetch=False, card_label=None):
    print("=== Hitster Card Generator ===\n")
    full_output_path = os.path.join(OUTPUT_DIR, output_dir)
    os.makedirs(full_output_path, exist_ok=True)
    json_file = os.path.join(OUTPUT_DIR, output_dir, "songs.json")
    
    songs = []

    # --- DATA FETCHING LOGIC ---
    if not fetch and os.path.exists(json_file):
        print(f"Step 1: Loading local data from {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            songs = json.load(f)
            
    elif os.path.exists(LINKS_FILE):
        print(f"Step 1: No JSON found. Using {LINKS_FILE} (Scraper Mode)...")
        songs = utils.fetch_no_api_data(LINKS_FILE)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(songs, f, indent=2)

    elif client_id and client_secret and playlist_url:
        print("Step 1: Fetching from Spotify API...")
        playlist_data = utils.fetch_spotify_playlist(playlist_url, client_id, client_secret)
        songs = utils.parse_playlist_data(playlist_data)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(songs, f, indent=2)
    else:
        print("ERROR: No API credentials AND no links.txt found.")
        return
    

    # --- CARD GENERATION ---
    print(f"\nStep 2: Generating {len(songs)} cards...")
    release_years = [song['year'] for song in songs]
    for i, song in enumerate(songs):
        qr_path = os.path.join(full_output_path, f"card_{i+1:03d}_qr.png")
        sol_path = os.path.join(full_output_path, f"card_{i+1:03d}_solution.png")
        
        qr_code = utils.create_qr_code(song['link'])
        utils.create_qr_with_neon_rings(qr_code, qr_path)
        utils.create_solution_side(song['name'], song['artist'], song['year'], release_years, sol_path)
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{len(songs)}...")

    # --- PDF CREATION ---
    print("\nStep 3: Creating PDF...")
    pdf_path = os.path.join(OUTPUT_DIR, f"{output_dir}.pdf")
    utils.create_cards_pdf(os.path.join(OUTPUT_DIR, output_dir), pdf_path)
    print(f"\n✓ Done! PDF ready at: {pdf_path}")

if __name__ == "__main__":

    load_dotenv()

    parser = argparse.ArgumentParser(description='Hitster Card Generator')
    parser.add_argument('--fetch', action='store_true', help='Force re-fetching data and remove existing songs.json')
    parser.add_argument('--ink-save-mode', action='store_true', default=None, help='if set, print the qr cards in ink saving mode (white background, black qr code)')
    parser.add_argument('--card-draw-border', action='store_true', default=None, help='if set, draw border around the qr cards for easier cutting')
    parser.add_argument('--card-label', default=None, help='Add a small label to each card (e.g., event name or playlist identifier)')
    parser.add_argument('--qr-bg-mode', choices=['transparent', 'solid'], default=None)
    parser.add_argument('--qr-bg-color', default=None)
    parser.add_argument('--qr-module-color', default=None)
    parser.add_argument('--qr-size-ratio', type=float, default=None)
    parser.add_argument('--bg-type', choices=['solid', 'neon_rings'], default=None)
    parser.add_argument('--game-title', default=None)
    parser.add_argument('--game-title-pos', default=None)
    args = parser.parse_args()

    PLAYLIST_URL = os.getenv("PLAYLIST_URL", "")
    CLIENT_ID = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

    INK_SAVING_MODE = os.getenv("INK_SAVING_MODE", "False").lower() == "true"
    CARD_DRAW_BORDER = os.getenv("CARD_DRAW_BORDER", "False").lower() == "true"
    CARD_LABEL = os.getenv("CARD_LABEL", None)
    
    QR_BG_MODE = os.getenv("QR_BG_MODE", "solid")
    QR_BG_COLOR = os.getenv("QR_BG_COLOR", "#FFFFFF")
    QR_MODULE_COLOR = os.getenv("QR_MODULE_COLOR", "#000000")
    QR_SIZE_RATIO = float(os.getenv("QR_SIZE_RATIO", "0.45"))
    BG_TYPE = os.getenv("BG_TYPE", "neon_rings")
    GAME_TITLE = os.getenv("GAME_TITLE", "")
    GAME_TITLE_POS = os.getenv("GAME_TITLE_POS", "top")

    ink_save_mode = args.ink_save_mode if args.ink_save_mode is not None else INK_SAVING_MODE
    card_draw_border = args.card_draw_border if args.card_draw_border is not None else CARD_DRAW_BORDER
    card_label = args.card_label if args.card_label is not None else CARD_LABEL

    db['ink_saving_mode'] = ink_save_mode
    db['card_draw_border'] = card_draw_border
    db['card_background_color'] = 'white' if ink_save_mode else 'black'
    db['card_border_color'] = 'black' if ink_save_mode else 'white'
    db['card_label'] = card_label
    
    db['qr_background_mode'] = args.qr_bg_mode if args.qr_bg_mode is not None else QR_BG_MODE
    db['qr_background_color'] = args.qr_bg_color if args.qr_bg_color is not None else QR_BG_COLOR
    db['qr_module_color'] = args.qr_module_color if args.qr_module_color is not None else QR_MODULE_COLOR
    db['qr_size_ratio'] = args.qr_size_ratio if args.qr_size_ratio is not None else QR_SIZE_RATIO
    db['qr_bg_type'] = args.bg_type if args.bg_type is not None else BG_TYPE
    db['qr_title'] = args.game_title if args.game_title is not None else GAME_TITLE
    db['qr_title_pos'] = args.game_title_pos if args.game_title_pos is not None else GAME_TITLE_POS
    db['qr_title_enabled'] = bool(db['qr_title'])

    print(f"Using client id {CLIENT_ID} to fetch playlist url {PLAYLIST_URL}...")
    print(f"Ink saving mode: {db['ink_saving_mode']}, Draw border: {db['card_draw_border']}, Label: {db['card_label']}\n")

    if args.fetch:
        json_file = os.path.join(OUTPUT_DIR, "hitster_cards", "songs.json")
        if os.path.exists(json_file):
            os.remove(json_file)
            print(f"Removed existing {json_file}")

    generate_hitster_cards(db, PLAYLIST_URL, CLIENT_ID, CLIENT_SECRET, fetch=args.fetch, card_label=db['card_label'])