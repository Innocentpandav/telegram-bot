import os
import io
import json
from typing import List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account

FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
if not FOLDER_ID:
    raise RuntimeError("GDRIVE_FOLDER_ID not set. Set it as an environment variable.")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Missing Google Drive service account JSON (set as secret: GDRIVE_SERVICE_ACCOUNT_JSON)")

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    if not SERVICE_ACCOUNT_JSON:
        raise RuntimeError("Missing Google Drive service account JSON (set as HF secret: GDRIVE_SERVICE_ACCOUNT_JSON)")

    creds_info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_file(local_file: str, remote_name: str):
    """Upload or update a file in Google Drive folder"""
    service = get_drive_service()
    file_metadata = {"name": remote_name, "parents": [FOLDER_ID]}
    media = MediaFileUpload(local_file, resumable=True)

    # Check if file exists
    results = service.files().list(
        q=f"name='{remote_name}' and '{FOLDER_ID}' in parents and trashed=false",
        fields="files(id)"
    ).execute()
    files = results.get("files", [])

    if files:
        file_id = files[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

def download_file(remote_name: str, local_file: str) -> bool:
    """Download a file from Google Drive folder"""
    service = get_drive_service()
    results = service.files().list(
        q=f"name='{remote_name}' and '{FOLDER_ID}' in parents and trashed=false",
        fields="files(id)"
    ).execute()
    files = results.get("files", [])
    if not files:
        return False

    file_id = files[0]["id"]
    request = service.files().get_media(fileId=file_id)

    with open(local_file, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    return True

def list_files_in_drive() -> List[str]:
    """List all files in the Google Drive folder"""
    service = get_drive_service()
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(name)"
    ).execute()
    return [f["name"] for f in results.get("files", [])]
