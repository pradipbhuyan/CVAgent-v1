import requests
from pathlib import Path
from graph_auth import get_graph_headers


ALLOWED_CV_TYPES = {".pdf", ".docx", ".txt"}


def list_drive_items(site_id: str, drive_id: str, folder_path: str):
    headers = get_graph_headers()
    folder_path = folder_path.strip("/")

    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}:/children"
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


def download_drive_file(site_id: str, drive_id: str, item_id: str):
    headers = get_graph_headers()
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()
    return response.content


def get_cv_files_from_folder(site_id: str, drive_id: str, folder_path: str):
    items = list_drive_items(site_id, drive_id, folder_path)
    files = filter_cv_files(items)

    results = []
    for item in files:
        content = download_drive_file(site_id, drive_id, item["id"])
        results.append({
            "name": item["name"],
            "content": content,
            "id": item["id"],
            "web_url": item.get("webUrl"),
        })

    return results
