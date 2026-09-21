# Educative Build Status Checker

A read-only tool that checks whether the custom Docker image has been built
successfully for a list of Educative course collections.

Educative's collection editor renders its build status with JavaScript and
requires an authenticated session, so plain HTTP requests aren't enough. This
tool drives a headless Chromium browser (Playwright) with a previously saved
login session, waits for the page to finish rendering, reads the status text,
and writes the results to a spreadsheet.

**The tool never modifies anything on Educative.** It only loads pages and
reads the rendered HTML — no buttons are clicked, no forms are submitted,
no builds are triggered.

## How it works

1. `save_session.py` opens a real browser window once so you can log in
   manually (including any 2FA). Your cookies and storage are saved to
   `auth_state.json`.
2. `check_build_bulk.py` reads `urls_template.xlsx`, builds a collection
   editor URL for each row, loads it in headless Chromium using the saved
   session, and looks for:
   - the text `Image has been built` → `built = True`
   - an element with class `.text-red-500` (error banner) → `built = False`
   - neither → `built` is blank (page didn't render as expected, or the
     session expired)
3. Results are written to `build_status_results.xlsx`.

## Files

| File | Purpose |
| --- | --- |
| `save_session.py` | One-time interactive login; creates `auth_state.json` |
| `check_build_bulk.py` | Main script; reads the input sheet and writes results |
| `urls_template.xlsx` | Input spreadsheet (see format below) |
| `build_status_results.xlsx` | Output spreadsheet, overwritten on every run |
| `auth_state.json` | Saved browser session — **contains login cookies, do not commit or share** |
| `requirements.txt` | Python dependencies |
| `debug_page.html` / `debug_screenshot.png` | Debug dump of the first URL, rewritten on every run |
| `venv/` | Local virtual environment (Python 3.9) |

## Input format

`urls_template.xlsx`, first sheet. Either:

**Option A — IDs (what the current template uses):**

| author_id | collection_id |
| --- | --- |
| 10370001 | 6616649039347712 |
| 10370001 | 6317860768448512 |

Each row becomes
`https://www.educative.io/editor/collectioneditor/<author_id>/<collection_id>`.

**Option B — full URLs:**

| url |
| --- |
| https://www.educative.io/editor/collectioneditor/10370001/6616649039347712 |

Column names are case-insensitive and whitespace is trimmed.

## Output format

`build_status_results.xlsx`:

| Column | Meaning |
| --- | --- |
| `url` | The page that was checked |
| `built` | `True` (image built), `False` (error shown), or blank (undetermined) |
| `status_text` | The status text read off the page |
| `error` | Page-load or parse failure, if any |

A blank `built` for every row usually means the saved session has expired —
re-run `save_session.py`.

## Setup

Requires Python 3.9 or newer.

```bash
cd "/Users/Basam_1/Desktop/ACDs/Python Script "

# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install the Chromium browser Playwright drives
playwright install chromium
```

A `venv/` with these dependencies is already present in this folder, so you can
skip straight to `source venv/bin/activate` if you're on the same machine.

## Running it

```bash
source venv/bin/activate

# One time only (and again whenever the session expires)
python3 save_session.py
```

A browser window opens. Log into Educative, complete any verification, then
return to the terminal and press Enter. This writes `auth_state.json`.

```bash
# Then, as often as you like
python3 check_build_bulk.py
```

Progress is printed per URL:

```
Loaded 49 URLs from urls_template.xlsx
[1/49] Checking https://www.educative.io/editor/collectioneditor/10370001/6616649039347712 ...
    -> built=True text='Image has been built'
...
Done. Results written to build_status_results.xlsx
```

Roughly 2–5 seconds per URL (a 2-second delay between requests plus page load
time), so about 3–4 minutes for 49 collections.

## Configuration

Settings are constants at the top of `check_build_bulk.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `INPUT_FILE` | `urls_template.xlsx` | Input spreadsheet |
| `OUTPUT_FILE` | `build_status_results.xlsx` | Output spreadsheet |
| `SHEET_NAME` | `0` | Sheet index or name to read |
| `REQUEST_DELAY_SECONDS` | `2` | Pause between pages, to stay gentle on the server |
| `PAGE_LOAD_TIMEOUT_MS` | `20000` | Per-page load timeout |
| `STATE_FILE` | `auth_state.json` | Saved session file |

## Troubleshooting

**`ERROR: auth_state.json not found`** — run `python3 save_session.py` first.

**Every row comes back blank** — the session expired, or you weren't fully
logged in when you pressed Enter. Delete `auth_state.json` and re-run
`save_session.py`. The first URL of each run also dumps
`debug_screenshot.png` and `debug_page.html`; open the screenshot to see what
the browser actually saw. The script prints a warning if it spots a "Log In"
button, which means the session isn't valid.

**`page load error: Timeout`** — the editor was slow to reach network idle.
Raise `PAGE_LOAD_TIMEOUT_MS`.

**`playwright: command not found` / browser not found** — activate the venv,
then run `playwright install chromium`.

## Notes

- `.env` contains an `EDUCATIVE_SECURE_AUTH` value left over from an earlier
  cookie-based approach. Neither script reads it today; authentication comes
  entirely from `auth_state.json`. It can be deleted.
- `auth_state.json` and `.env` grant access to your Educative account. Keep
  them out of version control — the included `.gitignore` covers
  `auth_state.json`, `.env`, `venv/`, and the `debug_*` files.
- `.refact/` holds Refact.ai assistant metadata and is unrelated to the tool.
