# Spotify Playlist Generator

A command-line tool to generate Spotify playlists based on your favorite artists.

## Prerequisites

- Python 3.6+
- Spotify Developer account (for client ID and client secret)

## Setup

1. Create a Spotify Developer application at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Note your Client ID and Client Secret
3. Add the callback URL you will use (default is `http://localhost:8888/callback`) as a Redirect URI in your Spotify application settings
4. Install the requirements:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python spotify_playlist_generator.py --artists "Artist Name1, Artist Name2" --playlist_name "My Awesome Playlist" --client_id YOUR_CLIENT_ID --client_secret YOUR_CLIENT_SECRET
```

### Arguments

- `--artists`: Comma-separated list of artist names
- `--playlist_name`: Name for the Spotify playlist to create (required unless --dryrun is used)
- `--sort`: Sort order for tracks - "date" (newest first), "popularity" (most popular first), or "name" (alphabetical). Default: "date"
- `--order`: Sort direction - "asc" (ascending) or "desc" (descending). Default: "asc"
- `--client_id`: Your Spotify API client ID
- `--client_secret`: Your Spotify API client secret
- `--callback_url`: Callback URL for Spotify authorization (default: http://localhost:8888/callback)
- `--dryrun`: Run in dry run mode (just print the tracks without creating a playlist)

### Authorization

When you run the tool to create a playlist (not in dry run mode), it will:

1. Open your default web browser to the Spotify authorization page
2. Ask you to log in to your Spotify account (if not already logged in)
3. Request permission to create playlists on your account
4. Redirect back to the application after you authorize

Your authorization is saved, so you won't need to repeat this process each time you use the tool.

#### Using a Custom Callback URL

If you're running the tool in an environment where the default localhost callback won't work (e.g., behind NAT, in a container), you can specify a custom callback URL:

```bash
python spotify_playlist_generator.py --artists "Artist Name" --playlist_name "My Playlist" --callback_url "https://your-domain.com/callback" --client_id YOUR_CLIENT_ID --client_secret YOUR_CLIENT_SECRET
```

Note: You must add this custom callback URL as a Redirect URI in your Spotify Developer application settings.

### Examples

Create a playlist with tracks from multiple artists:
```bash
python spotify_playlist_generator.py --artists "The Beatles, Pink Floyd" --playlist_name "Classic Rock Mix" --client_id YOUR_CLIENT_ID --client_secret YOUR CLIENT_SECRET
```

Create a K-pop playlist with tracks sorted alphabetically:
```bash
python spotify_playlist_generator.py --artists "BTS, Jung Kook, V, RM, SUGA, Jimin, Jin, J-Hope" --playlist_name "K-pop Favorites" --sort name --order asc --client_id YOUR_CLIENT_ID --client_secret YOUR CLIENT_SECRET
```

Create a playlist with the most popular tracks first:
```bash
python spotify_playlist_generator.py --artists "Radiohead" --playlist_name "Radiohead Hits" --sort popularity --order desc --client_id YOUR CLIENT_ID --client_secret YOUR CLIENT_SECRET
```

Preview tracks without creating a playlist:
```bash
python spotify_playlist_generator.py --artists "Queen" --dryrun --client_id YOUR CLIENT_ID --client_secret YOUR CLIENT_SECRET
```

## Notes

- When multiple artists match your search, you'll be prompted to select the correct one
- Your artist selections are remembered in `~/.spotify_playlist_generator_state.json`
- Only tracks where the artist is the primary artist are included (features are excluded)
- All tracks across all specified artists are sorted together as a single set
- The tool automatically handles Spotify API rate limits by waiting and retrying when necessary
- Authorization tokens are securely stored in the state file and refreshed automatically
