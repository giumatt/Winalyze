import os
import requests
import logging

def promote_to_alpha(wine_type: str) -> bool:
    """
    Promotes branch from testing to alpha on GitHub.
    
    Args:
        wine_type: Type of wine model being promoted ('red' or 'white')
        
    Returns:
        bool: True if merge was successful
    """
    try:
        token = os.environ.get("GITHUB_PAT")
        if not token:
            raise ValueError("GitHub PAT not found in environment variables")

        repo = "giumatt/Progetto-SDCC"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{repo}/merges"
        data = {
            "base": "alpha",
            "head": "testing",
            "commit_message": f"[AUTO] Promoted {wine_type} wine model to alpha after validation"
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 201:
            logging.info(f"Successfully merged testing -> alpha for {wine_type} model")
            return True
        elif response.status_code == 204:
            logging.info("No changes to merge")
            return True
        else:
            logging.error(f"GitHub merge failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logging.error(f"Error during branch promotion: {str(e)}")
        raise