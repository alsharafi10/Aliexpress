import requests
import base64
import json
import traceback

GITHUB_REPO = "alsharafi10/Aliexpress"
FILE_PATH = "data.json"
BRANCH = "main"

GIT_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/{FILE_PATH}"

import os
import sys

def log_msg(msg):
    try:
        log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(log_dir, "sync.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except:
        pass

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_data(token=""):
    """Downloads data.json from GitHub."""
    try:
        log_msg("Starting GitHub download...")
        headers = {}
        if token:
            headers["Authorization"] = f"token {token}"
            headers["Accept"] = "application/vnd.github.v3.raw"
        response = requests.get(RAW_URL, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    log_msg("Download success.")
                    return data
            except json.JSONDecodeError:
                log_msg("Downloaded content is not valid JSON")
        else:
            log_msg(f"Download failed with status: {response.status_code}")
    except Exception as e:
        log_msg(f"Network error during GitHub download: {e}")
    return None

def upload_data(transactions, token):
    """Uploads transactions to GitHub as data.json."""
    if not token:
        log_msg("Missing GitHub token in config. Skipping upload.")
        return False
        
    try:
        log_msg("Starting GitHub upload...")
        json_content = json.dumps(transactions, indent=4, ensure_ascii=False)
        content_bytes = json_content.encode('utf-8')
        base64_content = base64.b64encode(content_bytes).decode('utf-8')
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 1. Check if the file already exists to get its SHA
        get_resp = requests.get(GIT_API_URL, headers=headers, timeout=5, verify=False)
        sha = None
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
            
        # 2. Push the file
        payload = {
            "message": "Auto-sync data from Finance System",
            "content": base64_content,
            "branch": BRANCH
        }
        if sha:
            payload["sha"] = sha
            
        put_resp = requests.put(GIT_API_URL, headers=headers, data=json.dumps(payload), timeout=10, verify=False)
        
        if put_resp.status_code in [200, 201]:
            log_msg("Successfully uploaded data to GitHub.")
            return True
        else:
            log_msg(f"Failed to upload data to GitHub. HTTP Status: {put_resp.status_code} - {put_resp.text}")
    except Exception as e:
        log_msg(f"Error during GitHub upload: {e}")
        log_msg(traceback.format_exc())
        
    return False
