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
        logging.warning("⚠️ Merge non effettuato: conflitto o branch identici. Provo a creare una pull request...")

        # Crea una pull request da testing a alpha
        pr_url = f"https://api.github.com/repos/{repo}/pulls"
        pr_payload = {
            "title": "Auto PR: promote testing to alpha",
            "head": "testing",
            "base": "alpha",
            "body": "Promozione automatica dal branch testing al branch alpha dopo validazione modelli."
        }
        pr_response = requests.post(pr_url, headers=headers, json=pr_payload)
        if pr_response.status_code in [200, 201]:
            logging.info("✅ Pull request creata con successo.")
        elif pr_response.status_code == 422 and "A pull request already exists" in pr_response.text:
            logging.info("ℹ️ Pull request già esistente.")
        else:
            logging.error(f"❌ Creazione pull request fallita: {pr_response.status_code} - {pr_response.text}")
    else:
        logging.error(f"Merge fallito: {response.status_code} - {response.text}")