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

## Code development

This application was created almost entirely using an Android tablet, GitHub codespaces and Claude.
I was asked to make a Spotify playlist while away from my laptop/desktop and wanted to see how well these tools could take over for short term and relatively simple use cases like this.
The entire development process took around 2 hours with around 15 minutes of that time setting up what I was going to do.

Claude was very good at taking requirements and turning them into well structured, well written code.
There were several times when I asked it to rewrite large portions of the program:

- It started with the `spotipy` Python module, but that didn't work as cleanly as I wanted. All of the existing code was converted correctly first time from `spotipy` to direct REST requests.
- Claude correctly added code at the start to do the browser-based authentication necessary to authorize my Spotify app to my personal Spotify account. I didn't realize why this had happened and wanted to simplfy what I was working with early on. Claude removed the code on request. Later I realized I did in fact need that code. Claude added it back in correctly and modified other parts of the program as necessary.

Writing the code manually would probably have taken longer than 2 hours in any environment, and with more errors to work through. I would also have needed to read up and understand the Spotify Web API better early on. Instead I was able to spend my time thinking about features, potential bugs, reviewing code. I did need to read the Spotify API docs, but only enough to understand how they expected requests to look - this was how I found the minor issues in `spotipy` for my use case and decided to switch to making the requestsd directly.
