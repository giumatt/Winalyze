import os
import requests
import logging

def promote_to_alpha():
    token = os.getenv("GITHUB_PAT")
    repo = "giumatt/Progetto-SDCC"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    url = f"https://github.com/repos/{repo}/merges"
    data = {
        "base": "alpha",
        "head": "testing",
        "commit_message": "[AUTO] Automatic promotion after model validation"
    }

    r = requests.post(url, headers=headers, json=data)

    if r.status_code == 201:
        logging.info("Merge testing -> alpha completed")
    elif r.status_code == 204:
        logging.info("No merging needed")
    else:
        logging.error(f"GitHub merging error: {r.status_code} - {r.text}")
        raise Exception("GitHub merging error")