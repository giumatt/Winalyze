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
    logging.info(f"GitHub API merge response [{response.status_code}]: {response.text}")
    if response.status_code in [200, 201]:
        logging.info("✅ Merge eseguito correttamente.")
    elif response.status_code == 204:
        logging.info("ℹ️ Nessun cambiamento da unire. Merge non necessario.")
    elif response.status_code == 409:
        logging.warning("⚠️ Merge non effettuato: conflitto o branch identici.")
    else:
        logging.error(f"Merge fallito: {response.status_code} - {response.text}")