import base64
import json
import os

import requests
from airflow.models import Variable

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or Variable.get("GITHUB_TOKEN", default_var=None)

REPO_OWNER = "Slaterinn"
REPO_NAME = "godvinkaup"
FILE_PATH = "data/wines_json.json"
BRANCH = "master"
COMMIT_MESSAGE = "Auto-update wines_json.json from Airflow"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"


def get_file_sha():
    """Get current SHA of the file on GitHub (needed for updates)"""
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    resp = requests.get(API_URL + f"?ref={BRANCH}", headers=headers)
    if resp.status_code == 200:
        return resp.json()["sha"]
    elif resp.status_code == 404:
        # File does not exist, so no SHA needed for creation
        return None
    else:
        resp.raise_for_status()


def push_file_to_github(file_content: bytes):
    """Push file content (bytes) to GitHub repo"""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set")

    encoded_content = base64.b64encode(file_content).decode("utf-8")
    sha = get_file_sha()

    data = {
        "message": COMMIT_MESSAGE,
        "content": encoded_content,
        "branch": BRANCH,
    }
    if sha:
        data["sha"] = sha  # Needed if updating existing file

    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    response = requests.put(API_URL, headers=headers, data=json.dumps(data))
    if response.status_code in [200, 201]:
        print("File pushed successfully!")
    else:
        print("Failed to push file:", response.json())
        response.raise_for_status()


def run():
    local_file_path = "/opt/airflow/godvinkaup_website/data/wines_json.json"
    with open(local_file_path, "rb") as f:
        content_bytes = f.read()

    push_file_to_github(content_bytes)
