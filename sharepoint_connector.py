import requests
from pathlib import Path
from graph_auth import get_graph_headers
from urllib.parse import urlparse

ALLOWED_CV_TYPES = {".pdf", ".docx", ".txt"}

class RemoteUploadedFile:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content
        self._pos = 0

    def getvalue(self):
        return self._content

    def read(self):
        return self._content

    def seek(self, pos):
        self._pos = pos

def resolve_sharepoint_site_id(site_url: str) -> str:
    headers = get_graph_headers()

    parsed = urlparse(site_url)
    hostname = parsed.netloc
    site_path = parsed.path.strip("/")

    if not hostname or not site_path:
        raise ValueError("Invalid SharePoint site URL")

    url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}"
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    data = response.json()
    site_id = data.get("id")
    if not site_id:
        raise ValueError("Unable to resolve SharePoint site ID")

    return site_id


def list_site_drives(site_id: str):
    headers = get_graph_headers()
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json().get("value", [])


def resolve_drive_id_from_name(site_id: str, library_name: str = "Documents") -> str:
    drives = list_site_drives(site_id)
    for drive in drives:
        if str(drive.get("name", "")).strip().lower() == library_name.strip().lower():
            return drive["id"]

    if drives:
        # fallback to first available drive
        return drives[0]["id"]

    raise ValueError("No document library / drive found for this SharePoint site")


def list_drive_items(site_id: str, drive_id: str, folder_path: str):
    headers = get_graph_headers()
    folder_path = folder_path.strip("/")

    if folder_path:
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}:/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"

    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    return response.json().get("value", [])


def list_onedrive_items(drive_id: str, folder_path: str):
    headers = get_graph_headers()
    folder_path = folder_path.strip("/")

    if folder_path:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{folder_path}:/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"

    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    return response.json().get("value", [])


def filter_cv_files(items):
    files = []
    for item in items:
        if "file" not in item:
            continue

        name = item.get("name", "")
        suffix = Path(name).suffix.lower()
        if suffix in ALLOWED_CV_TYPES:
            files.append(item)

    return files


def download_sharepoint_file(site_id: str, drive_id: str, item_id: str):
    headers = get_graph_headers()
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()
    return response.content


def download_onedrive_file(drive_id: str, item_id: str):
    headers = get_graph_headers()
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()
    return response.content


def get_cv_files_from_sharepoint(site_url: str, folder_path: str, library_name: str = "Documents"):
    site_id = resolve_sharepoint_site_id(site_url)
    drive_id = resolve_drive_id_from_name(site_id, library_name)

    items = list_drive_items(site_id, drive_id, folder_path)
    files = filter_cv_files(items)

    results = []
    for item in files:
        content = download_sharepoint_file(site_id, drive_id, item["id"])
        results.append({
            "name": item["name"],
            "content": content,
            "id": item["id"],
            "web_url": item.get("webUrl"),
            "site_id": site_id,
            "drive_id": drive_id,
        })

    return results


def get_cv_files_from_onedrive(drive_id: str, folder_path: str):
    items = list_onedrive_items(drive_id, folder_path)
    files = filter_cv_files(items)

    results = []
    for item in files:
        content = download_onedrive_file(drive_id, item["id"])
        results.append({
            "name": item["name"],
            "content": content,
            "id": item["id"],
            "web_url": item.get("webUrl"),
            "drive_id": drive_id,
        })

    return results
