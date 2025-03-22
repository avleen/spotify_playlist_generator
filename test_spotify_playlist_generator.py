import unittest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
import spotify_playlist_generator as spg

class TestSpotifyPlaylistGenerator(unittest.TestCase):
    
    def setUp(self):
        # Set up test data
        self.test_state = {
            "artist_choices": {
                "Test Artist": {
                    "id": "test_id_123",
                    "name": "Test Artist Official"
                }
            },
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": 9999999999
        }
        
        # Sample artist data
        self.test_artist = {
            "id": "test_id_123",
            "name": "Test Artist Official",
            "followers": {"total": 1000}
        }
        
        # Sample album
        self.test_album = {
            "id": "album_123",
            "name": "Test Album",
            "release_date": "2023-01-01",
            "artists": [{"id": "test_id_123", "name": "Test Artist Official"}]
        }
        
        # Sample track
        self.test_track = {
            "id": "track_123",
            "name": "Test Track",
            "uri": "spotify:track:track_123",
            "album_release_date": "2023-01-01",
            "artists": [{"id": "test_id_123", "name": "Test Artist Official"}]
        }
    
    @patch('spotify_playlist_generator.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_load_state_file_exists(self, mock_exists, mock_file):
        # Set up the mocks
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.test_state)
        
        # Call the function under test
        result = spg.load_state()
        
        # Assertions
        mock_exists.assert_called_once_with(spg.STATE_FILE)
        mock_file.assert_called_once_with(spg.STATE_FILE, 'r')
        self.assertEqual(result, self.test_state)
    
    @patch('spotify_playlist_generator.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_load_state_file_not_exists(self, mock_exists, mock_file):
        # Set up the mocks
        mock_exists.return_value = False
        
        # Call the function under test
        result = spg.load_state()
        
        # Assertions
        mock_exists.assert_called_once_with(spg.STATE_FILE)
        mock_file.assert_not_called()
        self.assertEqual(result, {"artist_choices": {}})
    
    @patch('spotify_playlist_generator.open', new_callable=mock_open)
    def test_save_state(self, mock_file):
        # Call the function under test
        spg.save_state(self.test_state)
        
        # Assertions
        mock_file.assert_called_once_with(spg.STATE_FILE, 'w')
        # Instead of checking that write was called once, verify that the file handle was used
        mock_file_handle = mock_file()
        mock_file_handle.write.assert_called()
        
        # Capture all write calls and join them to reconstruct the full JSON string
        written_data = ''
        for call in mock_file_handle.write.call_args_list:
            written_data += call[0][0]
            
        # Check that the reconstructed JSON is valid and matches our state
        written_json = json.loads(written_data)
        self.assertEqual(written_json, self.test_state)
    
    @patch('spotify_playlist_generator.requests.post')
    def test_get_client_credentials_token_success(self, mock_post):
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_response
        
        # Call the function under test
        result = spg.get_client_credentials_token("test_id", "test_secret")
        
        # Assertions
        self.assertEqual(result, "test_token")
        mock_post.assert_called_once()
    
    @patch('spotify_playlist_generator.requests.post')
    def test_get_client_credentials_token_failure(self, mock_post):
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        # Call the function under test
        result = spg.get_client_credentials_token("test_id", "test_secret")
        
        # Assertions
        self.assertIsNone(result)
        mock_post.assert_called_once()
    
    @patch('spotify_playlist_generator.requests.get')
    def test_make_spotify_request_success(self, mock_get):
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response
        
        # Call the function under test
        result = spg.make_spotify_request("test_endpoint", "test_token")
        
        # Assertions
        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_once_with(
            "https://api.spotify.com/v1/test_endpoint",
            headers={"Authorization": "Bearer test_token"},
            params=None
        )
    
    @patch('spotify_playlist_generator.requests.get')
    def test_make_spotify_request_rate_limit(self, mock_get):
        # Set up the mock for rate limit response followed by success
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = '{"data": "test"}'
        success_response.json.return_value = {"data": "test"}
        
        mock_get.side_effect = [rate_limit_response, success_response]
        
        # Call the function under test with a small retry count to make test faster
        with patch('spotify_playlist_generator.time.sleep') as mock_sleep:
            result = spg.make_spotify_request("test_endpoint", "test_token", max_retries=1)
        
        # Assertions
        self.assertEqual(result, {"data": "test"})
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(1)
    
    @patch('spotify_playlist_generator.make_spotify_request')
    @patch('spotify_playlist_generator.load_state')
    def test_find_artist_from_cache(self, mock_load_state, mock_make_request):
        # Set up the mocks
        mock_load_state.return_value = self.test_state
        mock_make_request.return_value = self.test_artist
        
        # Call the function under test
        result = spg.find_artist("Test Artist", "test_token")
        
        # Assertions
        self.assertEqual(result, self.test_artist)
        mock_load_state.assert_called_once()
        mock_make_request.assert_called_once_with(
            "artists/test_id_123", "test_token"
        )
    
    @patch('spotify_playlist_generator.make_spotify_request')
    def test_get_artist_albums(self, mock_make_request):
        # Set up the mock
        mock_make_request.return_value = {
            "items": [self.test_album],
            "next": None
        }
        
        # Call the function under test
        result = spg.get_artist_albums("test_id_123", "test_token")
        
        # Assertions
        self.assertEqual(result, [self.test_album])
        mock_make_request.assert_called_once()
    
    def test_sort_tracks_by_date(self):
        # Create sample tracks with different dates
        tracks = [
            {"name": "Old Track", "album_release_date": "2010-01-01"},
            {"name": "New Track", "album_release_date": "2023-01-01"},
            {"name": "Middle Track", "album_release_date": "2015-01-01"}
        ]
        
        # Test ascending order
        result_asc = spg.sort_tracks(tracks, "date", "asc", "test_token")
        self.assertEqual(result_asc[0]["name"], "Old Track")
        self.assertEqual(result_asc[2]["name"], "New Track")
        
        # Test descending order
        result_desc = spg.sort_tracks(tracks, "date", "desc", "test_token")
        self.assertEqual(result_desc[0]["name"], "New Track")
        self.assertEqual(result_desc[2]["name"], "Old Track")
    
    def test_sort_tracks_by_name(self):
        # Create sample tracks with different names
        tracks = [
            {"name": "Track B"},
            {"name": "Track C"},
            {"name": "Track A"}
        ]
        
        # Test ascending order
        result_asc = spg.sort_tracks(tracks, "name", "asc", "test_token")
        self.assertEqual(result_asc[0]["name"], "Track A")
        self.assertEqual(result_asc[2]["name"], "Track C")
        
        # Test descending order
        result_desc = spg.sort_tracks(tracks, "name", "desc", "test_token")
        self.assertEqual(result_desc[0]["name"], "Track C")
        self.assertEqual(result_desc[2]["name"], "Track A")

if __name__ == '__main__':
    unittest.main()
