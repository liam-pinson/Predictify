# API Integration

## Spotify API

Used for track metadata retrieval.

### Scopes

- user-read-private
- user-read-email

### Example

```bash
GET https://api.spotify.com/v1/search?q=track_name&type=track
Authorization: Bearer <access_token>
```

## Google Gemini AI

Used to generate natural language producer insights per track.
