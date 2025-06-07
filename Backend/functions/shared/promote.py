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
    if response.status_code in [200, 201]:
        logging.info("Merge eseguito correttamente.")
    elif response.status_code == 204:
        logging.info("Nessun cambiamento da unire. Merge non necessario.")
    else:
        logging.error(f"Merge fallito: {response.status_code} - {response.text}")