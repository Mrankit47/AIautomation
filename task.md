# Task List: Integrations Health Checks & Token Refresh Script

- `[x]` Define Pydantic schemas in `backend/schemas/health.py` for integrations status
- `[x]` Implement `GET /health/integrations` in `backend/api/v1/health.py`
  - `[x]` Gemini API health check integration
  - `[x]` Groq API health check integration
  - `[x]` Instagram Account 1 (Gallery) health check integration
  - `[x]` Instagram Account 2 (Photography) health check integration
  - `[x]` YouTube API OAuth verification integration
  - `[x]` Pinterest API health check integration
  - `[x]` TikTok API health check integration
- `[x]` Write the token refresh and update tool in `scripts/refresh_instagram_token.py`
  - `[x]` Read credentials and access token from `.env`
  - `[x]` Call Meta API to exchange/refresh the token
  - `[x]` Verify new token validity against the Graph API
  - `[x]` Update the `.env` file safely with backup
- `[x]` Perform manual/automated verification
