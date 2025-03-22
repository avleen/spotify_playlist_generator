#!/usr/bin/env python3

import argparse
import sys
import json
import os
import requests
import base64
import time
from datetime import datetime
import webbrowser
import urllib.parse
import http.server
import socketserver
import threading

# State file to remember user choices
STATE_FILE = os.path.expanduser("~/.spotify_playlist_generator_state.json")
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_AUTH_BASE = "https://accounts.spotify.com"

# Add a global variable to store the authorization code from the callback
AUTH_CODE = None
AUTH_CODE_RECEIVED = threading.Event()

class AuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handler for the authorization callback."""
    def do_GET(self):
        global AUTH_CODE
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if 'code' in query_components:
            AUTH_CODE = query_components['code'][0]
            AUTH_CODE_RECEIVED.set()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html_content = """
            <html>
            <head><title>Spotify Authorization Successful</title></head>
            <body>
                <h1>Authorization Successful!</h1>
                <p>You have successfully authorized the Spotify Playlist Generator.</p>
                <p>You can close this window and return to the command line.</p>
            </body>
            </html>
            """
            
            self.wfile.write(html_content.encode('utf-8'))
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Authorization failed. Please try again.')
    
    def log_message(self, format, *args):
        # Suppress log messages
        return

def start_callback_server(callback_url):
    """Start a local server to receive the authorization callback."""
    try:
        parsed_url = urllib.parse.urlparse(callback_url)
        host = parsed_url.hostname
        port = parsed_url.port or 8888
        
        # Only start a local server if the callback is to localhost
        if host.lower() in ('localhost', '127.0.0.1'):
            server = socketserver.TCPServer((host, port), AuthCallbackHandler)
            
            # Run the server in a separate thread
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            return server
        else:
            print(f"Note: Using external callback URL {callback_url}")
            print("You'll need to configure this URL to handle the OAuth callback.")
            return None
    except Exception as e:
        print(f"Warning: Could not start callback server: {e}")
        print("You may need to manually copy the authorization code.")
        return None

def stop_callback_server(server):
    """Stop the callback server."""
    if server:
        server.shutdown()
        server.server_close()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate a Spotify playlist based on artist(s).')
    parser.add_argument('--artists', required=True, 
                        help='Comma-separated list of artist names (e.g., "BTS, Jung Kook, V")')
    parser.add_argument('--sort', default='date', choices=['date', 'popularity', 'name'],
                        help='Sort order for tracks (date, popularity, name). Default: date')
    parser.add_argument('--order', default='asc', choices=['asc', 'desc'],
                        help='Sort direction (asc, desc). Default: asc')
    parser.add_argument('--client_id', required=True, help='Spotify API client ID')
    parser.add_argument('--client_secret', required=True, help='Spotify API client secret')
    parser.add_argument('--callback_url', default='http://localhost:8888/callback',
                        help='Callback URL for Spotify authorization (default: http://localhost:8888/callback)')
    parser.add_argument('--dryrun', action='store_true', 
                        help='Print tracks instead of creating a playlist')
    parser.add_argument('--playlist_name', 
                        help='Name for the Spotify playlist to create (required unless --dryrun is used)')
    
    args = parser.parse_args()
    
    # Validate that playlist_name is provided unless in dryrun mode
    if not args.dryrun and (not args.playlist_name or args.playlist_name.strip() == ''):
        parser.error("--playlist_name is required and cannot be empty unless --dryrun is used")
    
    return args

def load_state():
    """Load saved state from file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    return {"artist_choices": {}}

def save_state(state):
    """Save state to file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving state file: {e}")

def get_client_credentials_token(client_id, client_secret):
    """Get a client credentials token for API operations."""
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(f"{SPOTIFY_AUTH_BASE}/api/token", headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"Error getting client credentials token: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()["access_token"]

def make_spotify_request(endpoint, token, method="GET", data=None, params=None, max_retries=5):
    """Make a request to the Spotify API with rate limit handling."""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    url = f"{SPOTIFY_API_BASE}/{endpoint}"
    
    retries = 0
    while retries <= max_retries:
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                headers["Content-Type"] = "application/json"
                response = requests.put(url, headers=headers, json=data)
            
            # Handle rate limiting (HTTP 429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                print(f"Rate limit exceeded. Waiting for {retry_after} seconds before retrying...")
                time.sleep(retry_after)
                retries += 1
                continue
            
            if response.status_code >= 400:
                print(f"Error making Spotify request: {response.status_code}")
                print(response.text)
                return None
            
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            if retries < max_retries:
                print(f"Retrying ({retries + 1}/{max_retries})...")
                time.sleep(2)  # Wait a bit before retrying
                retries += 1
                continue
            return None
    
    print(f"Maximum retries ({max_retries}) exceeded. Giving up.")
    return None

def find_artist(artist_name, client_token):
    """Find an artist by name and return their Spotify ID."""
    # Check if we have a saved choice for this artist name
    state = load_state()
    if "artist_choices" in state and artist_name in state["artist_choices"]:
        artist_id = state["artist_choices"][artist_name]["id"]
        artist_name_exact = state["artist_choices"][artist_name]["name"]
        print(f"Using saved artist: {artist_name_exact} (ID: {artist_id})")
        
        # Verify the artist still exists
        artist_data = make_spotify_request(f"artists/{artist_id}", client_token)
        if artist_data:
            return artist_data
        else:
            print(f"Saved artist ID no longer valid, searching again...")
            # Remove invalid entry
            if "artist_choices" in state:
                del state["artist_choices"][artist_name]
                save_state(state)
    
    # Search for artists
    params = {
        "q": artist_name,
        "type": "artist",
        "limit": 10
    }
    
    results = make_spotify_request("search", client_token, params=params)
    
    if not results or not results.get("artists", {}).get("items"):
        print(f"Artist '{artist_name}' not found.")
        return None
    
    artists = results["artists"]["items"]
    
    # If only one result, use it directly
    if len(artists) == 1:
        artist = artists[0]
        print(f"Found artist: {artist['name']} (ID: {artist['id']})")
        
        # Save this choice
        if "artist_choices" not in state:
            state["artist_choices"] = {}
        state["artist_choices"][artist_name] = {
            "id": artist['id'],
            "name": artist['name']
        }
        save_state(state)
        
        return artist
    
    # Multiple artists found, let user choose
    print(f"\nMultiple artists found for '{artist_name}':")
    for i, artist in enumerate(artists, 1):
        followers = artist.get('followers', {}).get('total', 0)
        print(f"{i}. {artist['name']} ({followers:,} followers)")
    
    # Get user choice
    while True:
        try:
            choice = input("\nEnter the number of the correct artist (or 'q' to skip): ")
            if choice.lower() == 'q':
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(artists):
                chosen_artist = artists[choice_idx]
                print(f"Selected: {chosen_artist['name']}\n")
                
                # Save this choice
                if "artist_choices" not in state:
                    state["artist_choices"] = {}
                state["artist_choices"][artist_name] = {
                    "id": chosen_artist['id'],
                    "name": chosen_artist['name']
                }
                save_state(state)
                
                return chosen_artist
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number or 'q'.")

def get_artist_albums(artist_id, client_token):
    """Get all albums for an artist."""
    albums = []
    offset = 0
    limit = 50
    
    while True:
        params = {
            "include_groups": "album,single",
            "limit": limit,
            "offset": offset
        }
        
        results = make_spotify_request(f"artists/{artist_id}/albums", client_token, params=params)
        
        if not results or not results.get("items"):
            break
        
        albums.extend(results["items"])
        
        if len(results["items"]) < limit or not results.get("next"):
            break
        
        offset += limit
    
    return albums

def get_album_tracks(album_id, client_token):
    """Get all tracks from an album."""
    tracks = []
    offset = 0
    limit = 50
    
    while True:
        params = {
            "limit": limit,
            "offset": offset
        }
        
        results = make_spotify_request(f"albums/{album_id}/tracks", client_token, params=params)
        
        if not results or not results.get("items"):
            break
        
        tracks.extend(results["items"])
        
        if len(results["items"]) < limit or not results.get("next"):
            break
        
        offset += limit
    
    return tracks

def get_artist_tracks(artist_id, client_token):
    """Get official tracks for an artist (excluding features)."""
    # Get artist's albums
    albums = get_artist_albums(artist_id, client_token)
    
    # Filter albums where the artist is the primary artist
    primary_albums = []
    
    for album in albums:
        # Check if our artist is the first/primary artist of the album
        if album['artists'] and any(a['id'] == artist_id for a in album['artists'][:1]):
            primary_albums.append(album)
    
    print(f"Found {len(primary_albums)} primary albums/singles out of {len(albums)} total")
    
    # Get tracks from each primary album
    all_tracks = []
    for album in primary_albums:
        tracks = get_album_tracks(album['id'], client_token)
        for track in tracks:
            # Only include tracks where our artist is a primary artist (first in the list)
            if any(a['id'] == artist_id for a in track['artists'][:1]):
                # Add album release date for sorting by date
                track['album_release_date'] = album['release_date']
                all_tracks.append(track)
    
    return all_tracks

def get_track_details(track_id, client_token):
    """Get detailed information about a track."""
    return make_spotify_request(f"tracks/{track_id}", client_token)

def sort_tracks(tracks, sort_method, sort_order, client_token):
    """Sort tracks based on the specified method and order."""
    reverse = sort_order.lower() == 'desc'
    
    if sort_method == 'date':
        # Sort by release date
        return sorted(tracks, key=lambda x: x.get('album_release_date', ''), reverse=reverse)
    elif sort_method == 'popularity':
        # Get track details to get popularity
        detailed_tracks = []
        print("\nFetching popularity data for tracks...")
        for i, track in enumerate(tracks, 1):
            if i % 10 == 0:
                print(f"Processing track {i}/{len(tracks)}...")
            detailed_track = get_track_details(track['id'], client_token)
            if detailed_track:
                detailed_tracks.append(detailed_track)
        # Sort by popularity
        return sorted(detailed_tracks, key=lambda x: x.get('popularity', 0), reverse=reverse)
    elif sort_method == 'name':
        # Sort by track name
        return sorted(tracks, key=lambda x: x['name'], reverse=reverse)
    else:
        return tracks

def get_user_auth_token(client_id, client_secret, callback_url):
    """Get a user authorization token using the authorization code flow."""
    # First, check if we have a saved token that's still valid
    state = load_state()
    current_time = time.time()
    
    if ("access_token" in state and "expires_at" in state and 
            state["expires_at"] > current_time + 120):  # Add buffer of 120 seconds
        print("Using saved access token")
        return state["access_token"]
    
    # If we have a refresh token, use it to get a new access token
    if "refresh_token" in state:
        print("Refreshing access token...")
        token_data = refresh_access_token(client_id, client_secret, state["refresh_token"])
        if token_data:
            # Save the new access token and expiration
            state["access_token"] = token_data["access_token"]
            state["expires_at"] = current_time + token_data["expires_in"]
            # Sometimes a new refresh token is provided
            if "refresh_token" in token_data:
                state["refresh_token"] = token_data["refresh_token"]
            save_state(state)
            return state["access_token"]
    
    # Parse the callback URL to get components
    parsed_url = urllib.parse.urlparse(callback_url)
    is_local_callback = parsed_url.hostname.lower() in ('localhost', '127.0.0.1')
    
    # Generate a random state value for security
    auth_state = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')
    
    # Scope needed for playlist operations
    scope = "playlist-modify-public playlist-modify-private user-read-private"
    
    # Construct the authorization URL
    auth_url = (
        f"{SPOTIFY_AUTH_BASE}/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"redirect_uri={urllib.parse.quote(callback_url)}&"
        f"scope={urllib.parse.quote(scope)}&"
        f"state={auth_state}"
    )
    
    # Start the callback server for localhost callbacks
    server = start_callback_server(callback_url)
    
    # Open the browser for authorization
    print("\nOpening your browser to authorize access to your Spotify account...")
    print(f"If your browser doesn't open automatically, visit this URL:\n{auth_url}\n")
    
    webbrowser.open(auth_url)
    
    # For local callbacks, wait for the callback server
    # For remote callbacks, prompt the user for the code
    if is_local_callback:
        print("Waiting for authorization... (check your browser)")
        AUTH_CODE_RECEIVED.wait(timeout=300)  # Wait up to 5 minutes
        
        # Stop the server
        stop_callback_server(server)
        
        auth_code = AUTH_CODE
    else:
        print("\nAfter authorizing in the browser, you will be redirected to your callback URL.")
        print("Please copy the 'code' parameter from the URL and paste it here.")
        auth_code = input("\nEnter the authorization code: ").strip()
    
    if not auth_code:
        print("Authorization failed or timed out.")
        return None
    
    # Exchange the authorization code for an access token
    token_data = exchange_auth_code(client_id, client_secret, auth_code, callback_url)
    
    if not token_data:
        print("Failed to get access token.")
        return None
    
    # Save the tokens
    state["access_token"] = token_data["access_token"]
    state["refresh_token"] = token_data["refresh_token"]
    state["expires_at"] = current_time + token_data["expires_in"]
    save_state(state)
    
    return token_data["access_token"]

def exchange_auth_code(client_id, client_secret, auth_code, redirect_uri):
    """Exchange an authorization code for access and refresh tokens."""
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }
    
    response = requests.post(f"{SPOTIFY_AUTH_BASE}/api/token", headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"Error exchanging code for tokens: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def refresh_access_token(client_id, client_secret, refresh_token):
    """Refresh an access token using a refresh token."""
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    response = requests.post(f"{SPOTIFY_AUTH_BASE}/api/token", headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"Error refreshing access token: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def get_current_user(token):
    """Get the current user's profile."""
    return make_spotify_request("me", token)

def create_playlist(token, user_id, name, description="", public=True):
    """Create a new playlist."""
    data = {
        "name": name,
        "description": description,
        "public": public
    }
    
    return make_spotify_request(f"users/{user_id}/playlists", token, method="POST", data=data)

def add_tracks_to_playlist(token, playlist_id, track_uris):
    """Add tracks to a playlist."""
    # Add tracks in batches of 100 (Spotify API limit)
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i:i+100]
        data = {"uris": batch}
        result = make_spotify_request(f"playlists/{playlist_id}/tracks", token, method="POST", data=data)
        if not result:
            print(f"Failed to add tracks {i+1} to {i+len(batch)} to playlist.")
            return False
    return True

def main():
    args = parse_arguments()
    
    try:
        # Get client credentials token for API operations
        client_token = get_client_credentials_token(args.client_id, args.client_secret)
        if not client_token:
            print("Failed to get client credentials token. Check your client ID and secret.")
            return
        
        # Split the comma-separated artist list and strip whitespace
        artist_list = [artist.strip() for artist in args.artists.split(',') if artist.strip()]
        
        if not artist_list:
            print("No artist names provided. Please specify at least one artist.")
            return
        
        # Find artists and their tracks
        all_tracks = []
        artist_names = []
        
        for artist_name in artist_list:
            artist = find_artist(artist_name, client_token)
            if artist:
                artist_names.append(artist['name'])
                tracks = get_artist_tracks(artist['id'], client_token)
                all_tracks.extend(tracks)
                print(f"Found {len(tracks)} tracks for {artist['name']}")
        
        if not all_tracks:
            print("No tracks found for the specified artists.")
            return
        
        # Remove duplicates (same track might appear in multiple albums)
        unique_tracks = []
        track_ids = set()
        for track in all_tracks:
            if track['id'] not in track_ids:
                track_ids.add(track['id'])
                unique_tracks.append(track)
        
        print(f"\nFound {len(unique_tracks)} unique tracks across all artists")
        
        # Sort all tracks as a single set
        sorted_tracks = sort_tracks(unique_tracks, args.sort, args.order, client_token)
        
        if args.dryrun:
            # Just print tracks
            sort_direction = "ascending" if args.order == "asc" else "descending"
            print(f"\nTracks (sorted by {args.sort}, {sort_direction}):")
            for i, track in enumerate(sorted_tracks, 1):
                artists = ", ".join([a['name'] for a in track['artists']])
                print(f"{i}. {track['name']} by {artists}")
        else:
            # Get a token for playlist creation with user authorization
            auth_token = get_user_auth_token(args.client_id, args.client_secret, args.callback_url)
            if not auth_token:
                print("Failed to get authorization token for playlist creation.")
                return
            
            # Get current user info
            user_info = get_current_user(auth_token)
            if not user_info:
                print("Failed to get user information. Make sure your credentials have the right permissions.")
                return
            
            user_id = user_info['id']
            print(f"Creating playlist for Spotify user: {user_info['display_name']} ({user_id})")
            
            # Create a description with artists' names
            artists_str = ", ".join(artist_names)
            playlist_description = f"Playlist of tracks by {artists_str}. Generated on {datetime.now().strftime('%Y-%m-%d')}."
            
            # Create playlist
            print(f"\nCreating playlist '{args.playlist_name}'...")
            playlist = create_playlist(auth_token, user_id, args.playlist_name, playlist_description)
            
            if not playlist:
                print("Failed to create playlist.")
                return
            
            # Add tracks to playlist
            print(f"Adding {len(sorted_tracks)} tracks to playlist...")
            track_uris = [track['uri'] for track in sorted_tracks]
            success = add_tracks_to_playlist(auth_token, playlist['id'], track_uris)
            
            if success:
                print(f"\nPlaylist created successfully: {playlist['external_urls']['spotify']}")
                print(f"Added {len(sorted_tracks)} tracks to the playlist.")
            else:
                print("\nPlaylist was created but there was an error adding some tracks.")
                print(f"Playlist URL: {playlist['external_urls']['spotify']}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
