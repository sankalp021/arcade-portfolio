# Internship & Placement Digest Bot

A tiny, zero-server bot that DMs Ipshita a **daily, curated list of real
internship and placement openings** in **sustainability / ESG and finance** —
tailored to her MBA (Sustainability Management, IIFM Bhopal) + B.Com Finance
background.

It runs on a **GitHub Actions** cron (free), finds openings with **Gemini +
Google Search grounding** (so links are real and current, not hallucinated),
tops that up with **real job-board APIs**, removes anything she's already been
sent, and pushes the digest to her over **Telegram**.

---

## How it works

```
GitHub Actions (daily cron, 08:00 IST)
        │
        ▼
  python src/main.py
   1. gemini_source.py → Gemini w/ Google Search grounding → live openings + real links
   2. boards.py        → Adzuna (India) + Remotive + The Muse + Jobicy + Greenhouse
                         (strict domain filter: sustainability/ESG/finance only)
   3. reddit_source.py → recent on-topic posts from relevant subreddits (public JSON)
   4. networking.py    → curated LinkedIn people/jobs deep-links + note templates
   5. dedupe.py        → drop anything in state/seen.json (already sent)
   6. formatter.py     → rank by fit, build a clean HTML message (Jobs / Reddit / Networking)
   7. telegram_client  → send to her Telegram chat
   8. commit state/seen.json back to the repo (so tomorrow won't repeat today)
```

**What she gets each day:** a ranked list of **real openings** (sustainability/ESG +
finance, India/remote), a short **Reddit** section of recent on-topic posts, and a
**LinkedIn networking** block — deep-links that open real people/recruiter and job
searches she can act on, plus copy-paste connection-note templates. The LinkedIn part
never invents people or scrapes profiles; it hands her live, pre-filtered searches.

**Why grounding matters:** a plain LLM call invents fake companies and dead
links. Grounding makes Gemini search Google in real time and answer from
current results, so what she gets is actually applyable.

---

## One-time setup (~15 min)

### 1. Create the Telegram bot
1. In Telegram, message **@BotFather** → `/newbot` → follow prompts.
2. It gives you a **bot token** like `123456:ABC-DEF...`. Keep it.

### 2. Get Ipshita's chat id
1. Have **Ipshita** open the bot and send it any message (e.g. `hi`).
2. Run (replace `<TOKEN>`):
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
3. Copy `result[0].message.chat.id` — that number is `TELEGRAM_CHAT_ID`.

### 3. Get the Gemini API key
You said you already have it. Otherwise: <https://aistudio.google.com/apikey>.

### 4. Add the three secrets to GitHub  ← this is where the key goes
In the bot's repo: **Settings → Secrets and variables → Actions → New
repository secret**. Add exactly these three (names must match):

| Secret name          | Value                                  |
| -------------------- | -------------------------------------- |
| `GEMINI_API_KEY`     | your Gemini key                        |
| `TELEGRAM_BOT_TOKEN` | the token from @BotFather              |
| `TELEGRAM_CHAT_ID`   | the chat id from step 2                |

**Optional (recommended for India coverage):** add `ADZUNA_APP_ID` and
`ADZUNA_APP_KEY` — free keys from [developer.adzuna.com](https://developer.adzuna.com).
Without them the Adzuna source is simply skipped; Reddit and LinkedIn need no keys.

> ⚠️ **Never paste these into the code or commit them.** Git history is
> forever and a leaked key gets abused fast. Secrets only ever live in the
> GitHub Secrets box (production) or a local `.env` (testing, gitignored).

### 5. Turn it on
The workflow runs daily on its own. To test it now: **Actions tab → "Daily
internship digest" → Run workflow**. Tick **dry_run** the first time to see the
output in the logs without messaging her.

---

## Tuning what it looks for

Everything is in [`config/profile.yaml`](config/profile.yaml) — roles,
locations, skills, keywords, and search terms. No code changes needed.

**TODO for you:** add the off-resume **sustainability internship (the "SI"
one)** under `notes:` — just the company name and a one-line description — so
the model weighs it when judging fit.

Optional knobs (set as extra repo secrets/variables or in `.env`):

| Var              | Default            | Meaning                                     |
| ---------------- | ------------------ | ------------------------------------------- |
| `MAX_ITEMS`      | `10`               | max openings per day                        |
| `GEMINI_MODEL`   | `gemini-3.5-flash` | which Gemini model to use                   |
| `DRY_RUN`        | `false`            | print instead of sending                    |
| `SEND_WHEN_EMPTY`| `false`            | send a note on days with nothing new        |

---

## Run it locally

```bash
cd internship-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in the three values
export $(grep -v '^#' .env | xargs)   # load .env into the shell
DRY_RUN=true python src/main.py       # prints the digest, sends nothing
```

Drop `DRY_RUN=true` to actually send to Telegram.

---

## Honest notes / limitations

- **Grounding is very good but not perfect.** Occasionally a surfaced listing
  may be a few days stale. Every item includes its source link so she can
  verify in one click, and dedupe means she never sees the same one twice.
- **Some days there won't be 10 genuinely-new roles.** The bot sends the best
  fresh ones rather than padding with junk — quality keeps her opening it.
- **We don't scrape Internshala / LinkedIn / Naukri directly** (they block
  bots and break constantly). Gemini's grounded search already reaches those
  listings via Google's index, with real links. `boards.py` adds clean API
  sources (Remotive, and optional Greenhouse company boards).
- **Cost:** Gemini Flash + a handful of Remotive calls per day is well within
  free/near-free tiers for a single daily run.

---

## Files

| Path                        | Role                                        |
| --------------------------- | ------------------------------------------- |
| `src/main.py`               | orchestrator                                |
| `src/gemini_source.py`      | Gemini + Google Search grounding            |
| `src/boards.py`             | Adzuna / Remotive / The Muse / Jobicy / Greenhouse |
| `src/reddit_source.py`      | recent on-topic posts (public Reddit JSON)  |
| `src/networking.py`         | LinkedIn people/jobs deep-links + templates |
| `src/dedupe.py`             | "already sent" state (`state/seen.json`)    |
| `src/formatter.py`          | ranking + Telegram HTML message building    |
| `src/telegram_client.py`    | Telegram Bot API sender                     |
| `src/config.py`             | env + profile loading                       |
| `config/profile.yaml`       | **what to search for — edit this**          |
| `.github/workflows/daily.yml` | the daily cron                            |
