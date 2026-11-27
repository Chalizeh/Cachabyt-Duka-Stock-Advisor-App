# Cachabyt Duka Stock Advisor

**WeCan Academy - Artificial Intelligence Course - Season 12 Group Project**
Group members: **Charles_1016, Eclare_2545, Caleb_2528**
Repo name: `wca-ai-tool-s12-cachabyt`

## What the tool does

Cachabyt Duka Stock Advisor is a Python command-line tool for a school canteen in Kenya. It:

- Manages canteen **stock** (view, add products, receive stock, low-stock alerts).
- Records **counter sales** and produces a **sales report** (counter sales + verified M-Pesa orders).
- Lets **customers** place advance orders and submit M-Pesa transaction codes.
- Lets the **owner** verify M-Pesa payments, send payment reminders, and track collection/delivery.
- Runs an **AI Stock Advisor** conversation (Gemini API) that:
  - remembers the whole session (full message history sent with **every** API call),
  - requires the model to reply in **JSON** and checks every reply, **retrying once** on failure,
  - makes a **final AI call** at the end of the session to summarise the conversation,
  - **saves** the conversation and summary to a dated file in `sessions/`.

## How to run

```bash
pip install -r requirements.txt
python cachabyt.py
```

Main menu:

1. Start a new AI advisor session
2. Open a past session file
3. Customer self-service centre
4. Duka owner/seller portal
5. Exit application

## How to set the API key

1. Look for file named `.env`.
2. Put your Gemini key in it:

```anthropic apikey="api key here"
``` ANTHROPIC_MODEL=claude-sonnet-5

The key is loaded with `python-dotenv` and is **never** written into the code.
`.env` is listed in `.gitignore`, so it cannot be committed by accident.

## Requirements

See `requirements.txt`:

- `google-genai` - Google Gemini API client
- `python-dotenv` - loads the API key from `.env`

## Project layout

```
wca-ai-tool-s12-cachabyt/
├── cachabyt.py   # the whole tool (17 numbered sections)
├── requirements.txt
├── .gitignore
├── .env
├── README.md
├── samples/
│   └── sample_session_2026-11-24.json   # a saved 4-turn test session
├── data/                   # created at runtime (stock, orders, sales)
└── sessions/               # created at runtime (saved AI sessions)
```

## Sample session

`samples/sample_session_2026-11-24.json` shows a real 4-turn test conversation
where the advisor remembers an earlier turn (note how turn 4 uses the product
asked about in turn 1). Copy it into `sessions/` to view it with menu option 2.

## GitHub collaboration

Every member has 3+ meaningful commits, e.g.:

- `Add message history to API call`
- `Add JSON answer check with one retry`
- `Add summary prompt and dated session save`
- `Fix JSON check on empty reply`
- `Add view past session menu option`
