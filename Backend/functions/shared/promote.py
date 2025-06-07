import logging
import os

def trigger_merge_to_alpha():
    import requests

    repo = "giumatt/Progetto-SDCC"
    github_token = os.getenv("GITHUB_PAT")
    url = f"https://api.github.com/repos/{repo}/merges"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    payload = {
        "base": "alpha",
        "head": "testing",
        "commit_message": "Auto merge to alpha after successful model validation"
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code not in [200, 201]:
        raise Exception(f"GitHub merge failed: {response.status_code} - {response.text}")
    logging.info("✅ Merge from testing to alpha executed.")