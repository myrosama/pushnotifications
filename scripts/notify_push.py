#!/usr/bin/env python3
"""
Posts the latest commit to a Telegram chat. Triggered by the pre-push git hook.
"""

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    ).stdout.strip()
)

env_path = REPO_ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def repo_url_and_name():
    remote = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        capture_output=True, text=True, cwd=REPO_ROOT
    ).stdout.strip()

    match = re.search(r"github\.com[:/](.+?)/(.+?)(\.git)?$", remote)
    if not match:
        return None, None
    owner, name = match.group(1), match.group(2)
    return f"https://github.com/{owner}/{name}", name


def latest_commit():
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%H|%h|%ad|%s", "--date=format:%B %d, %Y"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    full_hash, short_hash, date, subject = result.stdout.strip().split("|", 3)
    return full_hash, short_hash, date, subject


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram push notifier: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env, skipping.")
        return

    repo_url, repo_name = repo_url_and_name()
    if not repo_url:
        print("Telegram push notifier: couldn't determine GitHub repo from 'origin' remote, skipping.")
        return

    commit = latest_commit()
    if not commit:
        print("Telegram push notifier: no commits found, skipping.")
        return
    full_hash, short_hash, date, subject = commit

    text = (
        f"<b>{escape_html(repo_name)} Updates</b>\n"
        f"<b>Date:</b> {date}\n\n"
        f"<blockquote>- {escape_html(subject)}</blockquote>\n\n"
        f'🔗 Commit: <a href="{repo_url}/commit/{full_hash}">{short_hash}</a>'
    )

    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()

    request = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(f"Telegram push notifier: sent update for {short_hash} (HTTP {response.status})")
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        print(f"Telegram push notifier: failed ({error.code}) — {body}")


if __name__ == "__main__":
    main()
