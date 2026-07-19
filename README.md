# Telegram GitHub Push Notifier

Sends a Telegram message every time you push to a repo. It's one Python
script plus a git hook — copy two files into a repo, add a `.env`, done.
No server, no GitHub Actions, no cost.

## How it works

`scripts/notify_push.py` reads the latest commit (`git log -1`) and posts
it to the Telegram Bot API. `.githooks/pre-push` runs that script
automatically whenever you `git push`. The bot token and chat ID come from
a local `.env` file — **never committed** (it's gitignored).

The repo name and GitHub URL are read automatically from your `origin`
remote, so the same two files work unmodified in any repo — no per-repo
editing needed beyond the `.env`.

### Message format

```
DaemonClient Updates
Date: July 19, 2026

- Fix login bug

🔗 Commit: a1b2c3d
```
(bold title, bold "Date:" label, the commit subject in a quoted block,
and a linked short commit hash at the bottom.)

Only the latest commit is reported — matches what you just pushed.

## Setup

1. **Get a Telegram bot token.** Message [@BotFather](https://t.me/BotFather),
   send `/newbot`, follow the prompts, copy the token
   (`123456789:AAExampleTokenAbcDefGhi`).
2. **Get the target chat ID.**
   - Add the bot to the group (or start a DM with it for a personal chat).
   - Send any message in that chat.
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a
     browser and read the `"chat":{"id":...}` value from the response.
   - Or add [@RawDataBot](https://t.me/RawDataBot) to the group briefly —
     it prints the chat ID directly.
   - Group IDs are negative (`-123456789`); supergroups use a `-100`
     prefix (`-1001234567890`). If a group later gets upgraded to a
     supergroup, its ID changes.
3. **The bot must already be a member of the chat**, or sending fails with
   `{"ok":false,"description":"Bad Request: chat not found"}`.

## Adding this to a repo

1. Copy two things into the target repo, at the same paths:
   - `scripts/notify_push.py`
   - `.githooks/pre-push`
2. Create `.env` in the repo root (copy `.env.example` as a starting
   point) with your real values:
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAExampleTokenAbcDefGhi
   TELEGRAM_CHAT_ID=-1001234567890
   ```
   Make sure `.env` is in `.gitignore` — **never commit it.**
3. Point git at the committed hooks directory (one-time, per clone):
   ```bash
   git config core.hooksPath .githooks
   ```
4. Push. The hook runs `notify_push.py` before the push completes and
   posts the message.

Every teammate who wants notifications from their own pushes needs to run
step 3 locally and have their own `.env` — a git hook only runs on the
machine it's configured on, unlike CI. That's the tradeoff for not needing
any server or CI setup at all.

## Restricting to specific branches

The hook fires on every `git push`, from any branch. To only notify for
pushes to `main`, add a check near the top of `scripts/notify_push.py`'s
`main()`:

```python
current_branch = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True, text=True, cwd=REPO_ROOT
).stdout.strip()
if current_branch != "main":
    return
```

## Security notes

- Never put the bot token or chat ID in a committed file. `.env` is
  gitignored specifically so this can't happen by accident.
- If a token ever ends up committed anyway, treat it as compromised:
  revoke it immediately via `@BotFather` → your bot → **API Token** →
  **Revoke current token**, generate a new one, and update `.env`.
  Rewriting git history doesn't reliably scrub already-cached copies of a
  public commit — rotation is the only real fix.

## Troubleshooting

| Error | Meaning | Fix |
|---|---|---|
| `chat not found` | Bot isn't a member of the chat, or the ID is wrong/stale | Add the bot to the chat; re-check the ID (supergroup upgrades change it) |
| `Unauthorized` | Bot token is wrong or was revoked | Check `TELEGRAM_BOT_TOKEN` in `.env` |
| `Forbidden: bot was kicked from the group chat` | Bot was removed | Re-add the bot |
| Nothing happens on push | Hook isn't wired up | Run `git config core.hooksPath .githooks` in that clone |
| "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set" | No `.env`, or it's missing values | Create `.env` from `.env.example` and fill in real values |

## Repo layout

```
scripts/notify_push.py     # the notifier — copy into any repo
.githooks/pre-push         # the hook — copy into any repo, alongside the script
.env.example                # template for the .env you create per-repo (not committed)
docs/superpowers/specs/    # design spec for this project
docs/superpowers/plans/    # implementation plan for this project
```
