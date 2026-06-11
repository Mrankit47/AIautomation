from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly"
]

print("Starting OAuth...")

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    SCOPES
)

creds = flow.run_local_server(
    host="localhost",
    port=8080,
    access_type="offline",
    prompt="consent"
)

print("\nREFRESH TOKEN:")
print(creds.refresh_token)
print("Script Started")