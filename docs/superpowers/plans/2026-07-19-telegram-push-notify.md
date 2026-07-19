# Telegram GitHub Push Notifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A GitHub Actions workflow that sends a Telegram message to a specific group on every push, wired up in both `myrosama/pushnotifications` (canonical/demo repo) and `ABUKA-App/ABUKA-Backend` (real private repo), with a README explaining setup/reuse.

**Architecture:** Single self-contained workflow file (`telegram-push-notify.yml`) triggered on `push`. It reads commit info from the GitHub Actions event context, formats a message with `jq`/`sed`, and POSTs it to the Telegram Bot API with `curl`. No servers, no external services beyond GitHub Actions + Telegram.

**Tech Stack:** GitHub Actions (`ubuntu-latest` runner, has `curl`, `jq`, GNU `date`/`sed` preinstalled), Telegram Bot API, `gh` CLI for repo/secret management.

## Global Constraints

- Bot token and chat ID are stored ONLY as GitHub Actions encrypted secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) — never written into any file that gets committed.
- Message format (from spec): date at top, commit subject line as the "name" (bold), remaining commit message lines as the "description" (omitted if none), commit link at the bottom.
- Only the latest commit of a push is reported.
- Workflow must be a pure drop-in: no repo-specific parameters hardcoded, so the same file works unmodified in any repo once the two secrets are set.
- `ABUKA-App/ABUKA-Backend` must not be "distorted": only add the one workflow file, via a feature branch + PR (not a direct push to `main`), so the repo owner can review before it touches `main`.
- Bot token and chat ID are supplied out-of-band (not written in this document) and passed directly to `gh secret set` on the command line.

---

## Task 1: Create the workflow file in `pushnotifications`

**Files:**
- Create: `.github/workflows/telegram-push-notify.yml`

**Interfaces:**
- Produces: the complete, self-contained workflow file used verbatim in Task 4 (copied into `ABUKA-Backend`).

- [ ] **Step 1: Write the workflow file**

```yaml
name: Telegram Push Notification

on:
  push:

jobs:
  notify:
    runs-on: ubuntu-latest
    if: github.event.head_commit != null
    steps:
      - name: Send Telegram notification
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          COMMIT_MESSAGE: ${{ github.event.head_commit.message }}
          COMMIT_URL: ${{ github.event.head_commit.url }}
          COMMIT_TIMESTAMP: ${{ github.event.head_commit.timestamp }}
          COMMIT_AUTHOR: ${{ github.event.head_commit.author.name }}
          REPO_NAME: ${{ github.repository }}
          BRANCH_NAME: ${{ github.ref_name }}
        run: |
          set -euo pipefail

          SUBJECT=$(printf '%s' "$COMMIT_MESSAGE" | head -n1)
          BODY=$(printf '%s' "$COMMIT_MESSAGE" | tail -n +2 | sed '/^[[:space:]]*$/d')

          escape_html() {
            printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
          }
          SUBJECT_ESCAPED=$(escape_html "$SUBJECT")
          BODY_ESCAPED=$(escape_html "$BODY")

          DATE_STR=$(date -u -d "$COMMIT_TIMESTAMP" '+%b %-d, %Y %H:%M UTC')

          if [ -n "$BODY_ESCAPED" ]; then
            TEXT=$(printf '📅 %s\n🚀 <b>%s</b>\n\n%s\n\n📂 %s @ %s\n👤 pushed by %s\n\n🔗 %s' \
              "$DATE_STR" "$SUBJECT_ESCAPED" "$BODY_ESCAPED" "$REPO_NAME" "$BRANCH_NAME" "$COMMIT_AUTHOR" "$COMMIT_URL")
          else
            TEXT=$(printf '📅 %s\n🚀 <b>%s</b>\n\n📂 %s @ %s\n👤 pushed by %s\n\n🔗 %s' \
              "$DATE_STR" "$SUBJECT_ESCAPED" "$REPO_NAME" "$BRANCH_NAME" "$COMMIT_AUTHOR" "$COMMIT_URL")
          fi

          PAYLOAD=$(jq -n --arg chat_id "$TELEGRAM_CHAT_ID" --arg text "$TEXT" \
            '{chat_id: $chat_id, text: $text, parse_mode: "HTML", disable_web_page_preview: true}')

          HTTP_STATUS=$(curl -sS -o /tmp/telegram_response.json -w '%{http_code}' \
            -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -H 'Content-Type: application/json' \
            -d "$PAYLOAD")

          echo "Telegram API response (HTTP $HTTP_STATUS):"
          cat /tmp/telegram_response.json

          if [ "$HTTP_STATUS" -ne 200 ]; then
            echo "::error::Telegram API call failed with HTTP $HTTP_STATUS"
            exit 1
          fi
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/telegram-push-notify.yml'))" && echo VALID`
Expected: `VALID`

- [ ] **Step 3: Dry-run the message-building logic locally with mock data**

Run this to simulate the script's formatting logic without hitting Telegram (extracts the same commands the workflow uses):

```bash
COMMIT_MESSAGE=$'Fix login bug\n\nHandled expired tokens correctly.' \
COMMIT_URL='https://github.com/myrosama/pushnotifications/commit/abc123' \
COMMIT_TIMESTAMP='2026-07-19T14:32:10Z' \
COMMIT_AUTHOR='myrosama' \
REPO_NAME='myrosama/pushnotifications' \
BRANCH_NAME='main' \
bash -c '
set -euo pipefail
SUBJECT=$(printf "%s" "$COMMIT_MESSAGE" | head -n1)
BODY=$(printf "%s" "$COMMIT_MESSAGE" | tail -n +2 | sed "/^[[:space:]]*$/d")
escape_html() { printf "%s" "$1" | sed -e "s/&/\&amp;/g" -e "s/</\&lt;/g" -e "s/>/\&gt;/g"; }
SUBJECT_ESCAPED=$(escape_html "$SUBJECT")
BODY_ESCAPED=$(escape_html "$BODY")
DATE_STR=$(date -u -d "$COMMIT_TIMESTAMP" "+%b %-d, %Y %H:%M UTC")
TEXT=$(printf "📅 %s\n🚀 <b>%s</b>\n\n%s\n\n📂 %s @ %s\n👤 pushed by %s\n\n🔗 %s" \
  "$DATE_STR" "$SUBJECT_ESCAPED" "$BODY_ESCAPED" "$REPO_NAME" "$BRANCH_NAME" "$COMMIT_AUTHOR" "$COMMIT_URL")
jq -n --arg chat_id "<your-group-chat-id>" --arg text "$TEXT" "{chat_id: \$chat_id, text: \$text, parse_mode: \"HTML\"}"
'
```

Expected: valid JSON printed with a `"text"` field showing the formatted message (date line, bold subject, body, repo/branch/author lines, link) — confirms the `jq` payload is well-formed and the formatting matches spec.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/telegram-push-notify.yml
git commit -m "Add Telegram push-notification workflow"
```

---

## Task 2: Wire secrets into `pushnotifications` and verify end-to-end

**Files:**
- None created/modified (secrets + push only).

**Interfaces:**
- Consumes: `.github/workflows/telegram-push-notify.yml` from Task 1.

- [ ] **Step 1: Set the two secrets on the repo**

```bash
gh secret set TELEGRAM_BOT_TOKEN --repo myrosama/pushnotifications --body "<your-bot-token-from-BotFather>"
gh secret set TELEGRAM_CHAT_ID --repo myrosama/pushnotifications --body "<your-group-chat-id>"
```

Expected: both commands print `✓ Set Actions secret ...` with no error.

- [ ] **Step 2: Push the commit from Task 1 to trigger the workflow**

```bash
git push -u origin main
```

- [ ] **Step 3: Watch the triggered workflow run to completion**

```bash
gh run watch --repo myrosama/pushnotifications --exit-status
```

Expected: run status `completed` / `success`. If it fails, run `gh run view --repo myrosama/pushnotifications --log-failed` to see the curl/jq error and fix before proceeding.

- [ ] **Step 4: Confirm the Telegram API accepted the message**

```bash
gh run view --repo myrosama/pushnotifications --log | grep -A3 "Telegram API response"
```

Expected: `HTTP 200` followed by JSON containing `"ok":true`.

---

## Task 3: Write the README

**Files:**
- Create: `README.md`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Write the README**

Content requirements (all must be present):
- What this project does (one paragraph).
- Prerequisites: a Telegram bot (via @BotFather) and its token; the target group's chat ID (how to get it — add bot to group, send a message, hit `https://api.telegram.org/bot<TOKEN>/getUpdates`, or add `@userinfobot`/`@RawDataBot` to the group).
- Exact steps to add this to any repo: copy `.github/workflows/telegram-push-notify.yml`, set two repo secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) via GitHub UI (Settings → Secrets and variables → Actions → New repository secret) and via `gh secret set` as an alternative.
- What the message looks like (paste an example).
- How to restrict to specific branches (edit `on.push.branches: [main]` in the YAML — show the snippet).
- Note that the bot must be a member of the target group (and for supergroups, group privacy mode may need to be disabled via @BotFather's `/setprivacy` if the bot needs to read messages — not required just to send).
- Security note: never commit the token/chat ID; secrets only.

- [ ] **Step 2: Verify the README renders sensibly**

Run: `python3 -c "import pathlib; c = pathlib.Path('README.md').read_text(); assert '.github/workflows/telegram-push-notify.yml' in c and 'TELEGRAM_BOT_TOKEN' in c and 'TELEGRAM_CHAT_ID' in c; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Add setup README"
git push
```

---

## Task 4: Wire the workflow into `ABUKA-App/ABUKA-Backend` via branch + PR

**Files:**
- Create (in a separate local clone/worktree of `ABUKA-App/ABUKA-Backend`): `.github/workflows/telegram-push-notify.yml` (identical content to Task 1, Step 1).

**Interfaces:**
- Consumes: the exact YAML content produced in Task 1, Step 1.

- [ ] **Step 1: Set the two secrets on the ABUKA-Backend repo**

```bash
gh secret set TELEGRAM_BOT_TOKEN --repo ABUKA-App/ABUKA-Backend --body "<your-bot-token-from-BotFather>"
gh secret set TELEGRAM_CHAT_ID --repo ABUKA-App/ABUKA-Backend --body "<your-group-chat-id>"
```

Expected: both print `✓ Set Actions secret ...`.

- [ ] **Step 2: Clone into a scratch directory and create a branch**

```bash
git clone https://github.com/ABUKA-App/ABUKA-Backend.git /tmp/claude-1000/-home-sadrikov49-Desktop-pushnotifications/fb7910e1-c63b-4a73-a9d8-043388e02454/scratchpad/ABUKA-Backend
cd /tmp/claude-1000/-home-sadrikov49-Desktop-pushnotifications/fb7910e1-c63b-4a73-a9d8-043388e02454/scratchpad/ABUKA-Backend
git checkout -b add-telegram-push-notify
```

Expected: clone succeeds, on new branch `add-telegram-push-notify`.

- [ ] **Step 3: Add the workflow file (byte-identical to Task 1) and verify nothing else changed**

```bash
mkdir -p .github/workflows
# copy the exact file content from Task 1, Step 1
git status --short
```

Expected: `git status --short` shows exactly one new file: `.github/workflows/telegram-push-notify.yml` — nothing else touched.

- [ ] **Step 4: Commit and push the branch**

```bash
git add .github/workflows/telegram-push-notify.yml
git commit -m "Add Telegram push-notification workflow"
git push -u origin add-telegram-push-notify
```

- [ ] **Step 5: Watch the workflow run triggered by the branch push**

```bash
gh run watch --repo ABUKA-App/ABUKA-Backend --exit-status
```

Expected: `success`, and `gh run view --repo ABUKA-App/ABUKA-Backend --log | grep -A3 "Telegram API response"` shows `HTTP 200` / `"ok":true` — this is the live proof it works in the real repo, before anything touches `main`.

- [ ] **Step 6: Open a PR for the user to merge at their convenience**

```bash
gh pr create --repo ABUKA-App/ABUKA-Backend \
  --title "Add Telegram push-notification workflow" \
  --body "Adds .github/workflows/telegram-push-notify.yml — sends a Telegram message on every push. Secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are already set on this repo. Verified working on this branch (see Actions run)." \
  --head add-telegram-push-notify \
  --base main
```

Expected: PR URL printed. Do not merge automatically — report the URL and let the repo owner merge.

---

## Self-Review Notes

- Spec coverage: message format ✓ (Task 1), secrets-not-committed ✓ (Task 2/4 use `gh secret set`, never write to files), reusable drop-in ✓ (Task 3 README), verification on both repos ✓ (Task 2 Step 3-4, Task 4 Step 5), non-distorting wiring into ABUKA-Backend ✓ (Task 4 branch+PR, Step 3 status check).
- No placeholders: all code blocks are complete and runnable as written.
- Type/name consistency: env var names (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `COMMIT_MESSAGE`, etc.) are identical between Task 1's real file and Task 1 Step 3's dry-run simulation.
