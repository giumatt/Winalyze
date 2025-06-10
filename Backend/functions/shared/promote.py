import logging
import os
import requests

def trigger_merge_to_alpha():
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

    # Attempt to perform an automatic merge from 'testing' to 'alpha'
    response = requests.post(url, headers=headers, json=payload)
    logging.info(f"GitHub API merge response [{response.status_code}]: {response.text}")
    if response.status_code in [200, 201]:
        logging.info("Merge completed successfully.")
    elif response.status_code == 204:
        logging.info("No changes to merge. Merge not required.")
    elif response.status_code == 409:
        logging.warning("Merge not performed: conflict or identical branches. Attempting to create a pull request...")

        # If automatic merge fails due to conflicts, attempt to open a pull request instead
        pr_url = f"https://api.github.com/repos/{repo}/pulls"
        pr_payload = {
            "title": "Auto PR: promote testing to alpha",
            "head": "testing",
            "base": "alpha",
            "body": "Automatic promotion from testing to alpha branch after model validation."
        }
        pr_response = requests.post(pr_url, headers=headers, json=pr_payload)
        if pr_response.status_code in [200, 201]:
            logging.info("Pull request created successfully.")
        elif pr_response.status_code == 422 and "A pull request already exists" in pr_response.text:
            logging.info("A pull request already exists.")
        else:
            logging.error(f"Failed to create pull request: {pr_response.status_code} - {pr_response.text}")
    else:
        logging.error(f"Merge failed: {response.status_code} - {response.text}")