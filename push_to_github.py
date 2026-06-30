"""Create a new GitHub repo and push this project to it.

Reads PAT from /Users/mitsuyoshitsuha/claudetest/git.rtf (RTF wrapper OK; the
ghp_… / github_pat_… token is extracted by regex).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_TOKEN_FILE = Path("/Users/mitsuyoshitsuha/claudetest/git.rtf")
DEFAULT_OWNER = "tsuhasqni-pixel"
DEFAULT_REPO = "cost-variance-analytics"
DEFAULT_VISIBILITY = "public"


def read_token(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})", text)
    if not m:
        raise SystemExit(f"[ERROR] no GitHub PAT found in {p}")
    return m.group(1)


def api(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cost-variance-analytics-pusher",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"https://api.github.com{path}", data=body, headers=headers, method=method)
    with urlopen(req) as resp:
        text = resp.read().decode()
        return json.loads(text) if text else {}


def whoami(token: str) -> str:
    return api("GET", "/user", token).get("login", "")


def repo_exists(owner: str, repo: str, token: str) -> bool:
    try:
        api("GET", f"/repos/{owner}/{repo}", token)
        return True
    except Exception:
        return False


def create_repo(owner: str, repo: str, token: str, visibility: str, desc: str) -> None:
    me = whoami(token)
    is_org = me.lower() != owner.lower()
    payload = {
        "name": repo, "description": desc,
        "private": visibility == "private", "auto_init": False,
    }
    api("POST", f"/orgs/{owner}/repos" if is_org else "/user/repos", token, payload)


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def git_push(repo_dir: Path, owner: str, repo: str, token: str) -> None:
    env = os.environ.copy()
    clean_url = f"https://github.com/{owner}/{repo}.git"
    auth_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    if not (repo_dir / ".git").exists():
        run(["git", "init", "-b", "main"], repo_dir)
    cur = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(repo_dir), capture_output=True, text=True).stdout.strip()
    if not cur:
        run(["git", "remote", "add", "origin", clean_url], repo_dir)
    elif cur != clean_url:
        run(["git", "remote", "set-url", "origin", clean_url], repo_dir)
    run(["git", "add", "-A"], repo_dir)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_dir), capture_output=True, text=True).stdout.strip()
    has_commits = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), capture_output=True, text=True).returncode == 0
    if status or not has_commits:
        run(["git", "commit", "-m", "Update from cost-variance-analytics"], repo_dir)
    try:
        run(["git", "remote", "set-url", "origin", auth_url], repo_dir)
        run(["git", "push", "-u", "origin", "main"], repo_dir, env=env)
    finally:
        run(["git", "remote", "set-url", "origin", clean_url], repo_dir)


def enable_pages(owner: str, repo: str, token: str) -> None:
    try:
        api("POST", f"/repos/{owner}/{repo}/pages", token, {"source": {"branch": "main", "path": "/docs"}})
        print("[+] Pages enabled (main /docs)")
    except Exception as e:
        # Likely 409 — already enabled
        try:
            api("PUT", f"/repos/{owner}/{repo}/pages", token, {"source": {"branch": "main", "path": "/docs"}})
            print("[=] Pages already enabled; source updated to main /docs")
        except Exception as e2:
            print(f"[!] enable_pages: {e2}")
    try:
        api("POST", f"/repos/{owner}/{repo}/pages/builds", token)
        print("[+] Pages build triggered")
    except Exception as e:
        print(f"[!] trigger build: {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    ap.add_argument("--owner", default=DEFAULT_OWNER)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--visibility", choices=["public", "private"], default=DEFAULT_VISIBILITY)
    ap.add_argument("--desc", default="Statistical verification of cost variances (data import from internal-accounting)")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    token = read_token(args.token_file)
    print(f"GitHub login: {whoami(token)}")
    print(f"Target      : {args.owner}/{args.repo} ({args.visibility})")
    if not repo_exists(args.owner, args.repo, token):
        print("[+] creating remote repository ...")
        create_repo(args.owner, args.repo, token, args.visibility, args.desc)
    else:
        print("[=] remote repository already exists")
    git_push(here, args.owner, args.repo, token)
    enable_pages(args.owner, args.repo, token)
    print(f"\n[OK] pushed to https://github.com/{args.owner}/{args.repo}")
    print(f"[OK] Pages will be at https://{args.owner}.github.io/{args.repo}/")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] command failed: {e}", file=sys.stderr); sys.exit(1)
