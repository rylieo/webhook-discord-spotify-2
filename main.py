"""
Spotify to Discord Webhook Integration
Monitors currently playing Spotify track and sends updates to Discord webhook.
Includes Last.fm scrobble count integration.
"""

import base64
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, Any, Tuple

import requests
from colorthief import ColorThief
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "15"))

# Constants
TOKEN_EXPIRY_BUFFER = 300  # Refresh token 5 minutes before expiry
MAX_RETRIES = 3
RETRY_DELAY = 5

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("spotify_discord.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global state
access_token: Optional[str] = None
token_expiry: Optional[datetime] = None
headers: Dict[str, str] = {}
last_track_id: Optional[str] = None
profile: Optional[Dict[str, str]] = None
running = True


def validate_config() -> None:
    """Validate that all required environment variables are set."""
    required_vars = [
        "DISCORD_WEBHOOK_URL",
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_REFRESH_TOKEN",
        "LASTFM_API_KEY",
        "LASTFM_USERNAME"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        sys.exit(1)


def signal_handler(signum: int, frame: Any) -> None:
    """Handle graceful shutdown on SIGINT (Ctrl+C)."""
    global running
    logger.info("\nShutting down gracefully...")
    running = False
    sys.exit(0)


def get_dominant_color(image_url: str) -> int:
    """
    Extract dominant color from album art image.
    
    Args:
        image_url: URL of the album art image
        
    Returns:
        Integer representation of RGB color for Discord embed
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image_file = BytesIO(response.content)
        
        color_thief = ColorThief(image_file)
        r, g, b = color_thief.get_color(quality=1)
        
        return (r << 16) + (g << 8) + b
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch album art for color extraction: {e}")
        return 0x1DB954  # Spotify green as fallback
    except Exception as e:
        logger.warning(f"Failed to extract dominant color: {e}")
        return 0x1DB954


def get_total_scrobbles() -> str:
    """
    Fetch total scrobble count from Last.fm.
    
    Returns:
        String representation of total scrobbles, or "0" on failure
    """
    try:
        response = requests.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "user.getInfo",
                "user": LASTFM_USERNAME,
                "api_key": LASTFM_API_KEY,
                "format": "json",
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        return data.get("user", {}).get("playcount", "0")
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Last.fm scrobbles: {e}")
        return "0"
    except (KeyError, ValueError) as e:
        logger.warning(f"Failed to parse Last.fm response: {e}")
        return "0"


def refresh_access_token() -> Tuple[str, datetime]:
    """
    Refresh Spotify access token using refresh token.
    
    Returns:
        Tuple of (access_token, expiry_datetime)
        
    Raises:
        requests.RequestException: If token refresh fails
    """
    try:
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": SPOTIFY_REFRESH_TOKEN
            },
            headers={
                "Authorization": "Basic " + 
                base64.b64encode(
                    f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
                ).decode()
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        expiry = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info("Successfully refreshed access token")
        return access_token, expiry
        
    except requests.RequestException as e:
        logger.error(f"Failed to refresh access token: {e}")
        raise
    except KeyError as e:
        logger.error(f"Invalid token response: {e}")
        raise


def ensure_valid_token() -> None:
    """Ensure access token is valid, refresh if necessary."""
    global access_token, token_expiry, headers
    
    if (access_token is None or 
        token_expiry is None or 
        datetime.now() >= token_expiry - timedelta(seconds=TOKEN_EXPIRY_BUFFER)):
        
        access_token, token_expiry = refresh_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}


def get_profile() -> Dict[str, str]:
    """
    Fetch Spotify user profile information.
    
    Returns:
        Dictionary containing name, url, and avatar
        
    Raises:
        requests.RequestException: If API request fails
    """
    ensure_valid_token()
    
    try:
        response = requests.get(
            "https://api.spotify.com/v1/me",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "name": data["display_name"],
            "url": data["external_urls"]["spotify"],
            "avatar": data["images"][0]["url"] if data.get("images") else ""
        }
    except requests.RequestException as e:
        logger.error(f"Failed to fetch profile: {e}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse profile data: {e}")
        raise


def get_current_track() -> Optional[Dict[str, Any]]:
    """
    Fetch currently playing track from Spotify.
    
    Returns:
        Dictionary containing track data, or None if nothing is playing
        
    Raises:
        requests.RequestException: If API request fails
    """
    ensure_valid_token()
    
    try:
        response = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 204:
            return None
            
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch currently playing track: {e}")
        raise


def send_discord_webhook(payload: Dict[str, Any]) -> bool:
    """
    Send embed to Discord webhook.
    
    Args:
        payload: Discord webhook payload
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Discord webhook: {e}")
        return False


def process_track(data: Dict[str, Any]) -> None:
    """
    Process currently playing track and send to Discord if new.
    
    Args:
        data: Spotify currently playing response data
    """
    global last_track_id
    
    if not data or not data.get("item"):
        return
    
    item = data["item"]
    track_id = item.get("id")
    
    if not track_id or track_id == last_track_id:
        return
    
    try:
        # Extract track information
        artist_name = item["artists"][0]["name"]
        track_name = item["name"]
        album_name = item["album"]["name"]
        album_art = item["album"]["images"][0]["url"]
        track_url = item["external_urls"]["spotify"]
        
        # Get dynamic color from album art
        embed_color = get_dominant_color(album_art)
        
        # Get Last.fm stats
        total_scrobbles = get_total_scrobbles()
        
        # Build Discord embed payload
        payload = {
            "embeds": [
                {
                    "color": embed_color,
                    "author": {
                        "name": f"Now playing - {profile['name']}",
                        "url": f"https://www.last.fm/user/{LASTFM_USERNAME}",
                        "icon_url": profile["avatar"],
                    },
                    "title": track_name,
                    "url": track_url,
                    "description": f"**{artist_name}** • *{album_name}*",
                    "thumbnail": {"url": album_art},
                    "footer": {"text": f"{total_scrobbles} total scrobbles"},
                }
            ]
        }
        
        # Send to Discord
        if send_discord_webhook(payload):
            logger.info(f"Now playing: {artist_name} - {track_name}")
            last_track_id = track_id
        
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse track data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing track: {e}")


def main() -> None:
    """Main application loop."""
    global profile, running
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Validate configuration
    validate_config()
    
    # Initialize
    logger.info("Starting Spotify → Discord Webhook")
    logger.info(f"Polling interval: {POLLING_INTERVAL} seconds")
    
    retry_count = 0
    
    while running:
        try:
            # Fetch profile on first run or after errors
            if profile is None:
                profile = get_profile()
                logger.info(f"Connected as: {profile['name']}")
            
            # Get current track
            data = get_current_track()
            process_track(data)
            
            # Reset retry counter on success
            retry_count = 0
            
            # Sleep based on whether we're playing or not
            sleep_time = POLLING_INTERVAL if data else POLLING_INTERVAL * 2
            time.sleep(sleep_time)
            
        except requests.RequestException as e:
            retry_count += 1
            logger.warning(f"Request failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
            
            if retry_count >= MAX_RETRIES:
                logger.error("Max retries reached. Exiting.")
                break
            
            time.sleep(RETRY_DELAY)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            time.sleep(RETRY_DELAY)


if __name__ == "__main__":
    main()
