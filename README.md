# Telegram GitHub Push Notifier

Sends a Telegram message to a group (or user) every time someone pushes to
a GitHub repository. Runs entirely inside GitHub Actions — no server to
host, no cost beyond GitHub's free Actions minutes, and it's a single
drop-in YAML file.

## How it works

`.github/workflows/telegram-push-notify.yml` triggers on every `push`
event. It reads the latest commit's details straight from the GitHub
Actions context (no extra API calls), formats a message, and posts it to
the Telegram Bot API with `curl`. The bot token and chat ID are read from
GitHub Actions **encrypted secrets** — they are never written into the
workflow file or any other file in the repo.

### Message format

```
📅 Jul 19, 2026 21:46 UTC
🚀 Fix login bug

Handled expired tokens correctly.

📂 owner/repo @ main
👤 pushed by alice

🔗 https://github.com/owner/repo/commit/<sha>
```

- The **date** is the commit timestamp, shown in UTC.
- The **bold title** is the first line of the commit message.
- The **description** (if the commit message has more than one line) is
  everything after the first line. Single-line commits skip this block
  entirely — no empty gap.
- The **link** at the bottom goes straight to the commit on GitHub.

Only the most recent commit of a push is reported, even if a push
contains several commits — this keeps messages short and readable.

## Prerequisites

1. **A Telegram bot.** Message [@BotFather](https://t.me/BotFather) on
   Telegram, send `/newbot`, follow the prompts, and copy the token it
   gives you (looks like `123456789:AAExampleTokenAbcDefGhi`).
2. **The target chat ID.** For a group:
   - Add your bot to the group as a member.
   - Send any message in the group.
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a
     browser and look for `"chat":{"id":-100...` (or `-...` for a basic
     group) in the response — that number is your chat ID.
   - Alternatively, add [@RawDataBot](https://t.me/RawDataBot) or
     [@userinfobot](https://t.me/userinfobot) to the group briefly; it will
     print the chat ID directly.
   - Group chat IDs are negative numbers (e.g. `-123456789`). Supergroups
     use a `-100` prefix (e.g. `-1001234567890`). If a group later gets
     upgraded to a supergroup, its chat ID changes — Telegram will report
     `"chat not found"` for the old ID if that happens.
3. **The bot must be a member of the target chat.** Without that, every
   send attempt fails with `{"ok":false,"description":"Bad Request: chat
   not found"}`.

## Adding this to a repo

This works the same way in any repo — public or private:

1. Copy `.github/workflows/telegram-push-notify.yml` from this repo into
   the target repo, at the same path (`.github/workflows/`). Create that
   directory if it doesn't already exist. Nothing else in the target repo
   needs to change.
2. In the target repo on GitHub: **Settings → Secrets and variables →
   Actions → New repository secret**, and add two secrets:
   - `TELEGRAM_BOT_TOKEN` — your bot's token
   - `TELEGRAM_CHAT_ID` — the target chat ID
   
   Or via the `gh` CLI:
   ```bash
   gh secret set TELEGRAM_BOT_TOKEN --repo <owner>/<repo> --body "<your-bot-token>"
   gh secret set TELEGRAM_CHAT_ID --repo <owner>/<repo> --body "<your-chat-id>"
   ```
3. Push to any branch. The workflow fires and the message should arrive
   within a few seconds. Check **Actions** tab in the repo for the run log
   if it doesn't.

## Restricting to specific branches

By default the workflow fires on pushes to **every** branch. To limit it
to, say, only `main`, edit the `on:` block in the YAML:

```yaml
on:
  push:
    branches:
      - main
```

## Security notes

- Never put the bot token or chat ID directly in a committed file (YAML,
  README, plan, anything). Use GitHub Actions secrets exclusively — they
  are encrypted at rest and masked in logs.
- If a token is ever accidentally committed, treat it as compromised:
  revoke it immediately via `@BotFather` → your bot → **API Token** →
  **Revoke current token**, generate a new one, and update the
  `TELEGRAM_BOT_TOKEN` secret. Rewriting git history (or deleting the
  repo) does not reliably remove already-cached copies of a public
  commit — rotation is the only real fix.
- A chat ID alone isn't especially sensitive (it can't be used to send
  messages without a valid bot token), but there's no reason to expose it
  either — keep it in secrets too.

## Troubleshooting

| Telegram API error | Meaning | Fix |
|---|---|---|
| `Bad Request: chat not found` | Bot isn't a member of the chat, or the chat ID is wrong/stale | Add the bot to the chat; re-check the chat ID (supergroup upgrades change it) |
| `Unauthorized` | Bot token is wrong or was revoked | Check the `TELEGRAM_BOT_TOKEN` secret value |
| `Forbidden: bot was kicked from the group chat` | Bot was removed from the group | Re-add the bot |
| Workflow doesn't trigger at all | Workflow file isn't on the branch that was pushed, or isn't valid YAML | Confirm the file is present on that branch and check the Actions tab for parse errors |

## Repo layout

```
.github/workflows/telegram-push-notify.yml   # the workflow — copy this into any repo
docs/superpowers/specs/                      # design spec for this project
docs/superpowers/plans/                      # implementation plan for this project
```
