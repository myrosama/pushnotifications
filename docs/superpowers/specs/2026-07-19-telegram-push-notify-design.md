# Telegram GitHub Push Notifier — Design

## Purpose

Send a Telegram message to a specific group whenever a push happens on a
GitHub repository (primarily private repos). Must be free, serverless, and
"drop-in" — no server to host or maintain.

## Approach

A single GitHub Actions workflow file (`.github/workflows/telegram-push-notify.yml`)
triggered on the `push` event. GitHub Actions is free for this use case
(private repos on GitHub Free get 2,000 CI minutes/month; this job runs in
seconds) and requires no external hosting — it satisfies "serverless and
no cost" directly, and matches the user's own framing ("add it to the repo
active folder").

Rejected alternative: a webhook delivered to an external serverless function
(e.g. Cloudflare Worker). Also free, but requires provisioning and hosting a
separate endpoint and wiring a GitHub webhook to it — more moving parts than
necessary when GitHub Actions already runs natively inside the repo.

Rejected alternative: a local git hook (`post-commit`/`pre-push`). Doesn't
work for a team — only fires on the machine that has the hook installed, and
GitHub.com doesn't support server-side hooks for hosted repos.

## Behavior

- Trigger: `on: push` (all branches, by default).
- Source of truth for commit info: the `github.event.head_commit` context
  object available in the triggering workflow run — no extra API calls
  needed to fetch commit details.
- Only the latest commit of the push is reported (not every commit in a
  multi-commit push), keeping messages short.
- Message is sent via `curl` to `https://api.telegram.org/bot<TOKEN>/sendMessage`
  using Telegram's HTML `parse_mode`.
- The JSON payload is built with `jq --arg`, not string concatenation, so
  arbitrary commit message content (quotes, newlines) can't break the
  request. `&`, `<`, `>` in the commit message are escaped for HTML safety.

## Message format

```
📅 <human-readable date, UTC>
🚀 <b><first line of commit message — the "name"></b>

<remaining lines of commit message, if any — the "description">

📂 <owner/repo> @ <branch>
👤 pushed by <author>

🔗 <link to the commit>
```

If the commit message has no body (single-line commit), the description
line is simply omitted (no empty line clutter).

## Secrets

Two values are required and MUST be stored as GitHub Actions **encrypted
secrets** on each repo the workflow is added to — never committed to the
repo in plaintext:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The workflow YAML only ever references `${{ secrets.TELEGRAM_BOT_TOKEN }}`
and `${{ secrets.TELEGRAM_CHAT_ID }}`.

## Reusability

This repo (`myrosama/pushnotifications`) is the canonical home for the
workflow file plus documentation. Adding notifications to another repo is:

1. Copy `.github/workflows/telegram-push-notify.yml` into that repo's
   `.github/workflows/` directory (create the directory if it doesn't
   exist — purely additive, no other files touched).
2. Add the two secrets in that repo's Settings → Secrets and variables →
   Actions.
3. Push. Done.

No per-repo code changes or parameters needed — the workflow is entirely
self-contained and reads everything it needs from the GitHub Actions
context.

## Rollout / verification targets

1. **This repo** (`myrosama/pushnotifications`): secrets are set here via
   `gh secret set`, and the workflow file itself is added and pushed —
   that push is expected to trigger a real Telegram message, serving as
   the end-to-end test.
2. **`ABUKA-App/ABUKA-Backend`** (private repo, pnpm monorepo, no existing
   `.github/workflows` directory): the same workflow file is copied in
   verbatim and the same two secrets are set on that repo. Nothing else in
   that repo is modified — this is the "wire it to a working private repo
   without distorting it" requirement.

## Out of scope

- Multi-commit listing, PR events, issue events, deploy notifications —
  push-only, single latest commit, as scoped.
- Per-branch filtering/config — the workflow fires on every branch; can be
  restricted later by editing the `on.push.branches` key, documented in the
  README as an optional tweak.
- Any persistent server, database, or queue.

## Testing

No unit tests apply (this is a thin YAML + curl integration, not application
logic). Verification is a real push to both target repos and confirming the
Telegram message arrives in the group with correct content and a working
commit link.
