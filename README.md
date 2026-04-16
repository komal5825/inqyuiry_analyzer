# 🏗️ InquireAnti — Automated PEB Specification Agent

> **Infiniti Structures | Internal Tool**
> Automate client inquiry analysis and generate standardized Pre-Engineered Building (PEB) specification Excel sheets using AI.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Workflow](#workflow)
- [API Keys & Environment Variables](#api-keys--environment-variables)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Git — Pull & Push Guide](#git--pull--push-guide)
- [API Endpoints Reference](#api-endpoints-reference)
- [Extraction Schema](#extraction-schema)
- [Logic Engine Rules](#logic-engine-rules)
- [`.gitignore` Policy](#gitignore-policy)

---

## Overview

**InquireAnti** is a full-stack AI agent that reads client inquiry documents (emails, PDFs, images, Excel files) and automatically extracts Pre-Engineered Building (PEB) specifications using Google Gemini. The extracted data is processed through a business logic engine that applies 40+ engineering rules, defaults, and unit conversions, and the final output is a design-ready Excel specification sheet.

### Key Capabilities

| Feature | Details |
|---|---|
| Multi-format Input | `.txt`, `.pdf`, `.jpg/.png`, `.xlsx` |
| AI Extraction Engine | Google Gemini 2.5 Flash (8-phase deep analysis) |
| Logic Engine | 40+ engineering rules, defaults, bay spacing |
| Output | Excel file (`Infiniti Specification.xlsx` template populated) |
| Database | SQLite (stores all inquiries with status tracking) |
| Web UI | Glassmorphic drag-and-drop interface |

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Runtime |
| **FastAPI** | Latest | REST API framework |
| **Uvicorn** | Latest | ASGI server |
| **google-genai** (`google.genai`) | Latest | Gemini AI SDK |
| **SQLAlchemy** | Latest | ORM + SQLite |
| **openpyxl** | Latest | Excel file writing |
| **pdfplumber** | Latest | PDF text extraction |
| **pandas** | Latest | Excel reading for extraction |
| **Pillow (PIL)** | Latest | Image handling |
| **python-dotenv** | Latest | Environment variable loading |

### Frontend
| Technology | Purpose |
|---|---|
| **HTML5** | Structure |
| **Vanilla CSS** | Glassmorph styling, animations |
| **Vanilla JavaScript** | API calls, dynamic UI |
| **Google Fonts (Inter)** | Typography |

### Infrastructure
| Component | Technology |
|---|---|
| **Database** | SQLite (`peb_agent.db`) |
| **Static File Serving** | FastAPI `StaticFiles` mount |
| **File Storage** | Local `uploads/` directory |

---

## Project Structure

```
inquire_anti/
│
├── 📄 README.md                        ← You are here
├── 🔒 .env                             ← API keys (NOT committed to Git)
├── 📄 .gitignore                       ← Ignores .env, .db, uploads, venv, etc.
│
├── 📊 Infiniti Specification.xlsx      ← Master Excel template (base file for output)
├── 📄 Infiniti Specification for prompting.pdf  ← Reference spec for AI prompting
├── 📄 Email.txt                        ← Sample test inquiry email
│
├── 📁 backend/                         ← All Python server-side code
│   ├── __init__.py
│   ├── app.py                          ← FastAPI app, routes, request handling
│   ├── main.py                         ← CLI entry point (run agent directly)
│   ├── extractor.py                    ← PEBExtractor class (Gemini AI extraction)
│   ├── logic_engine.py                 ← Engineering rules, bay calc, defaults
│   ├── excel_filler.py                 ← Writes processed data into Excel template
│   ├── database.py                     ← SQLAlchemy models + SQLite config
│   └── uploads/                        ← Uploaded & generated files (git-ignored)
│
├── 📁 frontend/                        ← Static web interface
│   ├── index.html                      ← Main UI page
│   ├── style.css                       ← Glassmorphic CSS styles
│   └── script.js                       ← Fetch API calls, dynamic UI logic
│
└── 📁 .venv/                           ← Python virtual environment (git-ignored)
```

---

## Backend Architecture

### `app.py` — FastAPI Application
The main web server. Handles HTTP routes, file uploads, database sessions, and orchestrates the extraction → logic → Excel pipeline.

**Routes:**
- `GET /` → Serves `frontend/index.html`
- `POST /analyze` → Receives file/text, runs extraction + logic, stores to DB
- `POST /generate/{inquiry_id}` → Fills Excel template with verified data
- `GET /download/{inquiry_id}/{filename}` → Downloads the generated Excel file

---

### `extractor.py` — PEBExtractor (AI Core)
The brain of the system. Uses the **`google.genai`** SDK to send structured prompts to **Gemini 2.5 Flash**.

**Extraction methods:**
| Method | Input Type | How it works |
|---|---|---|
| `extract_from_text(text)` | Plain text / email | Sends text + system prompt to Gemini |
| `extract_from_pdf(pdf_path)` | PDF file | Uses `pdfplumber` to extract text pages, then calls `extract_from_text` |
| `extract_from_image(image_path)` | JPG/PNG | Sends PIL image + prompt to Gemini multimodal |
| `extract_from_excel(excel_path)` | Excel | Uses `pandas` to convert to structured text, then calls `extract_from_text` |
| `get_mock_data(source_type)` | Fallback | Returns a valid default JSON schema when extraction fails |

**8-Phase System Prompt:**
1. **Proposal ID Construction** — Extracts reference number + location
2. **Date Extraction** — Parses date into `YYYYMMDD` format
3. **Unit Conversion** — Converts all dimensions to meters (ft → m, inches → m)
4. **Height Logic** — Distinguishes "clear height" vs "eave height" (adds 1m for rafters/purlins)
5. **Area Calculation** — Length × Width in m²
6. **Structural Application** — Identifies building purpose
7. **Defaults** — Applies 40+ engineering defaults when client hasn't specified
8. **JSON Output** — Enforces strict nested JSON schema

**JSON Cleaning:** Strips `<think>` tags, removes markdown fences, extracts first `{...}` block, removes trailing commas.

---

### `logic_engine.py` — Engineering Rules Processor
Converts the raw nested JSON from the extractor into a **flat dictionary** for Excel population.

**Key calculations:**
| Rule | Logic |
|---|---|
| **Bay Spacing** | `num_bays = ceil(length / 8.0)`, `spacing = length / num_bays` |
| **Height** | Uses `left_eave_height_m` and `right_eave_height_m` directly from extractor |
| **Building Type** | `"Clear Span"` if width ≤ 30m, `"Multi-Span"` if width > 30m |
| **Skylights/Ventilators** | 2/bay for 15–30m width, 4/bay for >30m width |
| **Braced Bays** | `max(2, ceil(length / 40) + 1)` |
| **Canopy Height** | `door_height + 0.5m` (500mm above door per spec) |
| **Date Format** | `YYYYMMDD` → `dd-Mon-yy` |
| **Design Code Defaults** | AISC: dead=0.1, live=0.57 / IS: dead=0.15, live=0.75 |

---

### `excel_filler.py` — Excel Template Writer
Writes the flat processed dict into the **Infiniti Specification Excel template** using `openpyxl`.

**Sheet: `PEB Specifications`**
| Cells | Data |
|---|---|
| `C2–C10` | Project metadata (date, project, proposal ID, building no., area, etc.) |
| `C13–C29` | Geometry (length, width, heights, bay spacing, bracing, sheeting, doors) |
| `C32–C34` | Canopy (extension, slope, clear top height) |
| `C36–C38` | Accessories (braced bays, skylights, turbo ventilators) |
| `H2–H10` | Design parameters (code, dead/live/collateral loads, wind, seismic, etc.) |
| `H13–H16` | Deflection limits |
| `H21–H31` | Material grades |

**Sheet: `Crane & mezzanine`**
| Cells | Data |
|---|---|
| `C2–C8` | Crane specs (capacity, height, class, type, girder type) |
| `C18–C27` | Mezzanine specs (location, loads, dimensions, slab depth) |

---

### `database.py` — SQLite ORM
Uses **SQLAlchemy** with SQLite. Stores every inquiry run.

**`Inquiry` table schema:**
| Column | Type | Description |
|---|---|---|
| `id` | Integer | Primary key |
| `filename` | String | Auto-renamed uploaded file |
| `status` | String | `Extracting` → `Ready` |
| `raw_text` | Text | Pasted text input (if any) |
| `extracted_data` | JSON | Raw Gemini output |
| `processed_data` | JSON | Logic engine output |
| `created_at` | DateTime | UTC timestamp |

---

### `main.py` — CLI Runner
A standalone command-line script to run the full pipeline without the web server. Useful for testing with a specific file.

```bash
# Run with a specific file
python backend/main.py Email.txt

# Run with the default test image
python backend/main.py
```

---

## Frontend Architecture

**`frontend/index.html`** — Single-page application with 3 sections:
1. **Upload Section** — Drag-and-drop zone + text paste area + Analyze button
2. **Processing Section** — Progress bar + 3-step status indicator (Extracting → Logic Processing → Finalizing)
3. **Result Section** — Data grid showing extracted parameters with Edit Mode + Generate Excel button + Download link

**`frontend/script.js`** — JavaScript handles:
- File drag-and-drop events
- `POST /analyze` API call with `FormData`
- Dynamic rendering of the extracted data grid
- Edit mode toggling (makes fields editable)
- `POST /generate/{id}` API call for Excel generation
- Download link population

**`frontend/style.css`** — Glassmorphism design:
- Dark gradient background with blur effect
- Glass-effect containers (`backdrop-filter: blur`)
- Animated progress bar
- Inter font from Google Fonts

---

## Workflow

```
CLIENT INQUIRY
(Email / PDF / Image / Excel)
        │
        ▼
┌──────────────────────────────┐
│   FRONTEND (Browser)         │
│   Drag & Drop / Paste Text   │
│   POST /analyze              │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   FastAPI (app.py)           │
│   Save to DB (status:        │
│   "Extracting")              │
│   Route to correct extractor │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   PEBExtractor (extractor.py)│
│   Sends to Gemini 2.5 Flash  │
│   8-Phase System Prompt      │
│   Returns: nested JSON       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Logic Engine               │
│   (logic_engine.py)          │
│   Bay spacing, defaults,     │
│   height rules, unit checks  │
│   Returns: flat dict         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   FastAPI returns JSON       │
│   Update DB (status: "Ready")│
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   FRONTEND displays params   │
│   User reviews / edits       │
│   Clicks "Generate Excel"    │
│   POST /generate/{id}        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   excel_filler.py            │
│   Loads template .xlsx       │
│   Writes values to cells     │
│   Saves output file          │
└──────────────┬───────────────┘
               │
               ▼
       DOWNLOAD .xlsx
  Final_Spec_<Project>_<Date>.xlsx
```

---

## API Keys & Environment Variables

> ⚠️ **NEVER commit the `.env` file to Git.** It is listed in `.gitignore`.

Create a `.env` file in the project root:

```env
# Required — Primary AI extraction engine
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — Fallback / future use
HUGGINGFACE_TOKEN=your_huggingface_token_here
OPEN_AI_API_KEY=your_openai_key_here
```

### How to get keys

| Key | Where to get |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) → Create API Key |
| `HUGGINGFACE_TOKEN` | [HuggingFace Settings](https://huggingface.co/settings/tokens) → New Token |
| `OPEN_AI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) → Create Secret Key |

### How the keys are used

| Key | Used In | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | `extractor.py`, `app.py` | Powers Gemini 2.5 Flash for AI extraction — **REQUIRED** |
| `HUGGINGFACE_TOKEN` | Reserved for future models | Not actively used currently |
| `OPEN_AI_API_KEY` | Reserved for future fallback | Not actively used currently |

The key is loaded in `app.py`:
```python
load_dotenv(os.path.join(ROOT_DIR, ".env"))
api_key = os.getenv("GEMINI_API_KEY")
extractor = PEBExtractor(api_key=api_key)
```

---

## Setup & Installation

### Prerequisites
- **Python 3.10+** installed
- **Git** installed
- A valid `GEMINI_API_KEY` from Google AI Studio

### Step 1 — Clone the repository
```bash
git clone https://github.com/komal5825/inqyuiry_analyzer.git
cd inqyuiry_analyzer
```

### Step 2 — Create and activate virtual environment
```bash
# Create venv
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat

# Activate (Mac/Linux)
source .venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install fastapi uvicorn sqlalchemy python-dotenv openpyxl pdfplumber pandas pillow google-genai
```

### Step 4 — Create your `.env` file
```bash
# Create the file manually in the project root:
GEMINI_API_KEY=your_actual_key_here
```

> ⚠️ The `.env` file is **git-ignored** — every developer must create their own copy locally.

### Step 5 — Ensure the Excel template exists
- Confirm `Infiniti Specification.xlsx` is present in the project root.
- This file is the base template that gets populated with extracted data.
- It is also **git-ignored** (`.xlsx` excluded), so it must be placed manually.

---

## Running the Application

### Start the backend server
```bash
# From the project root, with .venv active:
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Access the UI
Open your browser and navigate to:
```
http://localhost:8000
```

### Run via CLI (no web server)
```bash
# Test with an email text file
python backend/main.py Email.txt

# Test with an image
python backend/main.py IMG_20260407_190835.jpg
```

---

## Git — Pull & Push Guide

### Repository
- **GitHub URL:** `https://github.com/komal5825/inqyuiry_analyzer`
- **Main branch:** `main`

---

### First-time setup (new machine)
```bash
# Clone
git clone https://github.com/komal5825/inqyuiry_analyzer.git
cd inqyuiry_analyzer

# Verify remote
git remote -v
```

---

### Pull latest changes (daily start)
```bash
# Always pull before starting work to avoid conflicts
git pull origin main
```

---

### Push your changes (daily workflow)

```bash
# 1. Check what changed
git status

# 2. Add only the files you changed (be selective, avoid adding .env or .db)
git add backend/extractor.py
git add backend/logic_engine.py
git add frontend/script.js
# OR add all tracked changes (safe, since .gitignore protects sensitive files)
git add .

# 3. Commit with a clear message
git commit -m "fix: corrected height logic in logic_engine and updated extractor prompt"

# 4. Push to GitHub
git push origin main
```

---

### Commit message convention
Use prefixes to keep history readable:

| Prefix | When to use |
|---|---|
| `feat:` | New feature added |
| `fix:` | Bug fix |
| `refactor:` | Code restructuring (no behavior change) |
| `docs:` | README or documentation updates |
| `chore:` | Dependency updates, config changes |

**Examples:**
```
feat: add mezzanine load extraction to extractor
fix: strip think tags from Gemini response before JSON parse
docs: update README with API key instructions
chore: add pdfplumber to requirements
```

---

### Force push (only if history was rewritten)
```bash
# Used after git filter-branch or rebasing — use with caution
git push -f origin main
```
> ⚠️ Force push rewrites remote history. Only do this if you intentionally rewrote commits (e.g., removing secrets).

---

### Undoing mistakes

```bash
# Undo last commit (keeps changes in working directory)
git reset --soft HEAD~1

# Discard all local uncommitted changes
git checkout -- .

# See commit history
git log --oneline -10
```

---

### What is git-ignored (never push these)

| Pattern | Reason |
|---|---|
| `.env` | Contains API keys — **NEVER expose** |
| `*.db` | SQLite database files |
| `__pycache__/` | Python bytecode |
| `.venv/` | Virtual environment |
| `uploads/` | User-uploaded files |
| `*.xlsx` | Excel files (template + output) |
| `*.jpg`, `*.png` | Image files |

---

## API Endpoints Reference

### `POST /analyze`
Accepts a file upload or plain text and runs the full extraction + logic pipeline.

**Request (multipart/form-data):**
| Field | Type | Description |
|---|---|---|
| `file` | File (optional) | `.pdf`, `.txt`, `.jpg`, `.png`, `.xlsx` |
| `text` | String (optional) | Pasted inquiry email text |

**Response:**
```json
{
  "id": 1,
  "data": {
    "proposal_id": "Q-1516-Palghar",
    "date": "09-Apr-26",
    "project": "Warehouse",
    "length": 60.0,
    "width": 24.0,
    ...
  },
  "upload_feedback": {
    "name": "Q-1516_Palghar_09-Apr-26.txt",
    "type": "text/plain"
  }
}
```

---

### `POST /generate/{inquiry_id}`
Fills the Excel template with verified (possibly user-edited) data.

**Request body:** JSON dict of the processed data (same shape as `data` in `/analyze` response).

**Response:**
```json
{
  "download_url": "/download/1/Final_Spec_Warehouse_09-Apr-26.xlsx"
}
```

---

### `GET /download/{inquiry_id}/{filename}`
Downloads the generated Excel file.

---

## Extraction Schema

The Gemini extractor returns a **nested JSON** with this structure:

```json
{
  "proposal_id": "Q-1516-Palghar",
  "raw_date": "20260409",
  "location": "Palghar",
  "structure_application": "Warehouse",
  "design_code": "AISC",
  "design_software": "MBS",
  "building_no": 1,
  "option": 1,
  "revision": 0,

  "dimensions": {
    "length_m": 60.0,
    "width_m": 24.0,
    "left_eave_height_m": 8.0,
    "right_eave_height_m": 8.0,
    "height_type_given": "clear",
    "area_sqm": 1440.0,
    "roof_slope": "10/100",
    "ridge_line_distance_m": 12.0,
    "block_wall_m": 3.0,
    "building_type": "Clear Span"
  },

  "loads": { ... },
  "sheeting": { ... },
  "openings": { ... },
  "crane": { ... },
  "mezzanine": { ... },
  "canopy": { ... },
  "accessories": { ... },
  "material_grades": { ... },
  "deflection_limits": { ... },
  "notes": "..."
}
```

---

## Logic Engine Rules

| Rule | Value |
|---|---|
| Max bay spacing | 8.0 m |
| Building type threshold | 30 m (≤30m = Clear Span, >30m = Multi-Span) |
| Clear height → Eave height | Clear + 1.0 m |
| Canopy height | Door height + 0.5 m |
| Braced bays | `max(2, ceil(length/40) + 1)` |
| Skylights/Ventilators (width 15–30m) | 2 per bay |
| Skylights/Ventilators (width >30m) | 4 per bay |
| Default design code | AISC |
| AISC dead load | 0.10 kN/m² |
| AISC live load | 0.57 kN/m² |
| IS dead load | 0.15 kN/m² |
| IS live load | 0.75 kN/m² |
| Default wind speed | 39 m/s |
| Default seismic coefficient | 0.16 |
| Default roof slope | 10/100 |
| Default sheeting | 0.45mm aluzinc |
| Default door size | 3×3 m |

---

## `.gitignore` Policy

The following are **never tracked** by Git:

```gitignore
.env          # API keys
*.env

__pycache__/  # Python cache
*.pyc

venv/         # Virtual environment

*.db          # SQLite databases

uploads/      # All uploaded/generated files
backend/uploads/

*.xlsx        # Excel templates and outputs
*.jpg         # Image files
*.png
```

> ⚠️ If you accidentally committed `.env` or a secret key, run:
> ```bash
> git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all
> git push -f origin main
> ```
> Then rotate/regenerate all exposed API keys immediately.

---

## 📞 Project Info

| Field | Detail |
|---|---|
| **Project Name** | InquireAnti — PEB Specification Agent |
| **Company** | Infiniti Structures |
| **Repository** | [komal5825/inqyuiry_analyzer](https://github.com/komal5825/inqyuiry_analyzer) |
| **AI Model** | Google Gemini 2.5 Flash |
| **Design Code** | AISC (default), IS (on client request) |
| **Design Software** | MBS |

---

*© 2026 InquireAnti AI. Built for PEB Precision.*
