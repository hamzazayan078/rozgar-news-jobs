"""
Zero-Dependency GitHub Repo Sync (Pure Python Stdlib)
----------------------------------------------------
Uploads project files from e:\\champion directly to a GitHub repository using the
GitHub Contents REST API (`urllib.request` + `base64`), so no local `git.exe`
installation is needed.

Usage:
  set GITHUB_TOKEN=ghp_your_token
  python github_sync.py --owner YOUR_USERNAME --repo rozgar-news-jobs
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import time
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.github.com"
TIMEOUT_SECONDS = 60

# Only push source, workflow, docs, state, and README files (skip __pycache__ / local tools).
SYNC_INCLUDE_PATHS = [
    ".github/workflows/auto-fetch-jobs.yml",
    "auto_job_magic.py",
    "blogger-magic-jobs-theme.xml",
    "docs/index.html",
    "docs/jobs.json",
    "docs/posters.html",
    "github_sync.py",
    "MONETIZATION_GUIDE.md",
    "README.md",
    "test_auto_job_magic.py",
]


def github_request(
    method: str,
    endpoint: str,
    token: str,
    payload: dict | None = None,
) -> dict:
    """Send an authenticated JSON request to the GitHub REST API."""
    url = f"{API_BASE}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "RozgarNewsSync/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected) as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def get_existing_file_sha(owner: str, repo: str, repo_path: str, branch: str, token: str) -> str | None:
    """Return existing blob SHA if the file already exists in the target repo."""
    encoded_path = urllib.parse.quote(repo_path)
    endpoint = f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/contents/{encoded_path}?ref={urllib.parse.quote(branch)}"
    try:
        info = github_request("GET", endpoint, token)
        return info.get("sha")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def build_upsert_payload(
    *,
    content_bytes: bytes,
    message: str,
    branch: str,
    existing_sha: str | None = None,
) -> dict:
    """Construct the GitHub Contents API PUT payload with base64 content."""
    payload: dict[str, str] = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha
    return payload


def sync_files_to_github(
    *,
    root_dir: Path,
    owner: str,
    repo: str,
    branch: str = "main",
    token: str,
) -> int:
    """Upload all configured project files to GitHub and return uploaded count."""
    uploaded = 0
    for rel_path in SYNC_INCLUDE_PATHS:
        local_file = root_dir / rel_path
        if not local_file.exists():
            continue
        sha = get_existing_file_sha(owner, repo, rel_path, branch, token)
        payload = build_upsert_payload(
            content_bytes=local_file.read_bytes(),
            message=f"chore: sync {rel_path}",
            branch=branch,
            existing_sha=sha,
        )
        encoded_path = urllib.parse.quote(rel_path)
        endpoint = f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/contents/{encoded_path}"
        try:
            github_request("PUT", endpoint, token, payload=payload)
            print(f"[SYNCED] {rel_path}")
            uploaded += 1
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and ".github/workflows" in rel_path:
                print(f"[NOTE] {rel_path} requires 'workflow' PAT scope; will sync via GitHub UI.")
                continue
            raise
    return uploaded


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for pushing workspace files to GitHub without git.exe."""
    parser = argparse.ArgumentParser(description="Push Rozgar News project files to GitHub via REST API")
    parser.add_argument("--owner", required=True, help="GitHub username or org")
    parser.add_argument("--repo", required=True, help="Target GitHub repository name")
    parser.add_argument("--branch", default="main", help="Target branch (default: main)")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("[ERROR] Set GITHUB_TOKEN environment variable first.")
        return 1

    root_dir = Path(__file__).resolve().parent
    count = sync_files_to_github(
        root_dir=root_dir,
        owner=args.owner,
        repo=args.repo,
        branch=args.branch,
        token=token,
    )
    raw_feed = f"https://raw.githubusercontent.com/{args.owner}/{args.repo}/{args.branch}/docs/jobs.json"
    print(f"[DONE] Synced {count} files. Your Blogger externalFeedUrl is:\n{raw_feed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

