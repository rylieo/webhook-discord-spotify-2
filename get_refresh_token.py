"""
Spotify Refresh Token Generator
Run this script once to generate a refresh token for your Spotify application.
The refresh token will be printed to the console and can be added to your .env file.
"""

import base64
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-currently-playing user-read-playback-state"

# Validate configuration
if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env file")
    print("Please add these to your .env file before running this script.")
    sys.exit(1)

auth_url = (
    "https://accounts.spotify.com/authorize"
    f"?client_id={CLIENT_ID}"
    "&response_type=code"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope={SCOPE}"
)


class Handler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass
    
    def do_GET(self):
        """Handle OAuth callback from Spotify."""
        try:
            # Parse authorization code from callback
            query_params = parse_qs(urlparse(self.path).query)
            
            if "error" in query_params:
                error = query_params["error"][0]
                print(f"\n❌ Authorization failed: {error}")
                self.send_error(400, f"Authorization failed: {error}")
                raise SystemExit
            
            if "code" not in query_params:
                print("\n❌ No authorization code received")
                self.send_error(400, "No authorization code received")
                raise SystemExit
            
            code = query_params["code"][0]
            
            # Exchange code for tokens
            response = requests.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI
                },
                headers={
                    "Authorization": "Basic " + base64.b64encode(
                        f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
                    ).decode()
                },
                timeout=10
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            if "refresh_token" not in token_data:
                print("\n❌ No refresh token in response")
                self.send_error(500, "No refresh token received")
                raise SystemExit
            
            refresh_token = token_data["refresh_token"]
            
            # Success!
            print("\n" + "=" * 70)
            print("✅ Successfully obtained refresh token!")
            print("=" * 70)
            print(f"\nSPOTIFY_REFRESH_TOKEN={refresh_token}")
            print("\nAdd this to your .env file to complete the setup.")
            print("=" * 70 + "\n")
            
            # Send success response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <head><title>Success!</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #1DB954;">Success!</h1>
                    <p>Your refresh token has been generated.</p>
                    <p>Check your terminal for the token and add it to your .env file.</p>
                    <p>You can close this window now.</p>
                </body>
                </html>
            """)
            
            raise SystemExit
            
        except requests.RequestException as e:
            print(f"\n❌ Failed to exchange code for token: {e}")
            self.send_error(500, f"Token exchange failed: {e}")
            raise SystemExit
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.send_error(500, f"Unexpected error: {e}")
            raise SystemExit


if __name__ == "__main__":
    print("=" * 70)
    print("Spotify Refresh Token Generator")
    print("=" * 70)
    print("\nOpening browser for Spotify authorization...")
    print("Please log in and authorize the application.")
    print("\nWaiting for callback...")
    
    try:
        webbrowser.open(auth_url)
        HTTPServer(("127.0.0.1", 8888), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
