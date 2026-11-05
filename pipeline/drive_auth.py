"""Access token for reading the Google Drive inbox (read-only).

Preferred: GDRIVE_SA_JSON, the JSON key of a Google Cloud service account. The owner shares the inbox
folder with that service account's email (Viewer). Private, no OAuth consent screen, no restricted-scope
verification. Nothing is public.

Fallback: GDRIVE_REFRESH_TOKEN (OAuth, drive.readonly), used only if no service account key is set.
Both return a bearer token, or None when neither secret is set.
"""
import json
import os

import requests

SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def configured():
    return bool(os.environ.get("GDRIVE_SA_JSON") or os.environ.get("GDRIVE_REFRESH_TOKEN"))


def using():
    if os.environ.get("GDRIVE_SA_JSON"):
        return "service account"
    if os.environ.get("GDRIVE_REFRESH_TOKEN"):
        return "OAuth refresh token"
    return None


WRITE_SCOPE = "https://www.googleapis.com/auth/drive"  # service account only: update files the owner shared as Editor


def access_token(scope=SCOPE):
    if os.environ.get("GDRIVE_SA_JSON"):
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        info = json.loads(os.environ["GDRIVE_SA_JSON"])
        creds = service_account.Credentials.from_service_account_info(info, scopes=[scope])
        creds.refresh(Request())
        return creds.token
    if os.environ.get("GDRIVE_REFRESH_TOKEN"):
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
            "refresh_token": os.environ["GDRIVE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
        r.raise_for_status()
        return r.json()["access_token"]
    return None
