import os
import requests
from typing import Optional

def github_has_open_pr(owner: str, repo: str, title_prefix: str) -> bool:
    """
    Check if there is an open PR in the repo authored by Jules bot with the given title prefix.
    """
    token = os.environ.get("TRIAGE_GH_TOKEN") or os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Warning: No GitHub token (TRIAGE_GH_TOKEN, GH_PAT, GITHUB_TOKEN) set. Skipping deduplication check.")
        return False

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    params = {
        "state": "open",
        "per_page": 100 # Should be enough for recent PRs
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        prs = response.json()

        for pr in prs:
            # Check author
            user = pr.get("user", {})
            login = user.get("login", "")
            if "google-labs-jules" in login or login == "google-labs-jules[bot]":
                # Check title
                title = pr.get("title", "")
                if title_prefix.lower() in title.lower():
                    return True
        return False
    except Exception as e:
        print(f"Warning: Failed to check GitHub PRs for {owner}/{repo}: {e}")
        return False
