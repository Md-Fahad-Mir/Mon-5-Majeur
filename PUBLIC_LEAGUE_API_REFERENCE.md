# Public League API Quick Reference

## Base URL
All endpoints are prefixed with `/api/`

## Authentication
All endpoints require JWT authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Public League Management

### Create Public League
```http
POST /api/public-leagues/
Content-Type: application/json

{
  "leauge_name": "My Public League",
  "leauge_description": "A fun public league for everyone",
  "leauge_logo": "lakers",
  "team_budget": "100M",
  "max_team_number": "10"
}
```

### List My Created Public Leagues
```http
GET /api/public-leagues/
```

### Get Public League Details
```http
GET /api/public-leagues/{league_id}/
```

### Update Public League
```http
PUT /api/public-leagues/{league_id}/
Content-Type: application/json

{
  "leauge_name": "Updated League Name",
  "leauge_description": "Updated description"
}
```

### Delete Public League
```http
DELETE /api/public-leagues/{league_id}/
```

## Joining & Leaving

### List Available Public Leagues
```http
GET /api/public-leagues/active_leagues/
```

### Join Public League
```http
POST /api/public-leagues/join/
Content-Type: application/json

{
  "league_id": 1
}
```

### List My Joined Public Leagues
```http
GET /api/public-leagues/my_leagues/
```

### Leave Public League
```http
POST /api/public-leagues/leave/
Content-Type: application/json

{
  "league_id": 1
}
```

## League Management (Creator Only)

### Kick Team from League
```http
POST /api/public-leagues/kick/
Content-Type: application/json

{
  "league_id": 1,
  "team_id": 5
}
```

### Start League
```http
POST /api/public-leagues/start_league/
Content-Type: application/json

{
  "league_id": 1
}
```

## Match Management

### List Public League Matches
```http
GET /api/public-leagues/matches/?league_id=1&match_type=regular_season
```

### Get Today's Matches
```http
GET /api/public-leagues/matches/my-matches-today/
```

### Get Match Details
```http
GET /api/public-leagues/matches/{league_id}/{match_day}/
```

## Player Selection

### Get Player Selection for Match
```http
GET /api/public-leagues/{league_id}/{match_day}/players-selection/
```

### Update Player Selection
```http
POST /api/public-leagues/{league_id}/{match_day}/players-selection/
Content-Type: application/json

{
  "selected_players": [
    {
      "id": "player_id_1",
      "name": "LeBron James",
      "position": "F",
      "team": "Lakers",
      "team_id": "team_id",
      "price": "2.5M"
    },
    {
      "id": "player_id_2",
      "name": "Stephen Curry",
      "position": "G",
      "team": "Warriors",
      "team_id": "team_id",
      "price": "2.3M"
    }
  ]
}
```

## League Statistics

### Get League Standings
```http
GET /api/public-leagues/{league_id}/standings/?match_type=regular_season
```

### Get Season Information
```http
GET /api/public-leagues/{league_id}/season/
```

### Get Playoff Qualifiers
```http
GET /api/public-leagues/{league_id}/playoff-qualifiers/
```

### Get League Winner
```http
GET /api/public-leagues/{league_id}/winner/
```

## WebSocket Connection

### Connect to League Updates
```javascript
const ws = new WebSocket('ws://your-domain/ws/public-leagues/{league_id}/');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event);
  console.log('Payload:', data.payload);
};
```

### WebSocket Events
- `team_joined` - A new team joined the league
- `team_left` - A team left the league
- `team_kicked` - A team was kicked from the league
- `league_started` - The league has started

## Response Examples

### Public League Object
```json
{
  "id": 1,
  "creator": 1,
  "leauge_name": "My Public League",
  "leauge_description": "A fun public league",
  "leauge_logo": "lakers",
  "team_budget": "100M",
  "max_team_number": "10",
  "teams": [
    {
      "team_id": 1,
      "team_name": "Team Alpha",
      "team_logo": "logo_url"
    }
  ],
  "created_at": "2026-01-24T01:00:00Z",
  "start_date": null,
  "is_ready": false,
  "is_started": false,
  "is_active": true,
  "current_match_day": 0
}
```

### Match Object
```json
{
  "id": 1,
  "league_id": 1,
  "league_name": "My Public League",
  "match_day": 1,
  "match_type": "regular_season",
  "match_date": "2026-01-25T00:00:00Z",
  "status": "scheduled",
  "player_scores": [],
  "pairs": [
    {
      "player_a_id": 1,
      "player_a_name": "Team Alpha",
      "player_b_id": 2,
      "player_b_name": "Team Beta",
      "score_a": 0,
      "score_b": 0
    }
  ],
  "created_at": "2026-01-24T01:00:00Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Error message describing what went wrong"
}
```

### 403 Forbidden
```json
{
  "detail": "Only the league creator can perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "League not found."
}
```

## Notes

- All dates are in ISO 8601 format (UTC)
- Player selection is limited to 5 players per match
- Total player price must not exceed the league budget
- Matches can only be edited when status is "scheduled"
- Only the league creator can start, update, or delete the league
- League creator cannot leave their own league
