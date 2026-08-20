# Project Kickoff Prompt — Self-Hosted Nutrition Tracker

Copy everything below into Claude Code (or another CLI coding agent) to start the build.

---

## Prompt

I want to build a self-hosted, open-source nutrition/calorie tracking app — an alternative to Fitatu/MyFitnessPal, for personal use first, designed to eventually be open-sourced on GitHub. Set up the initial project structure and first working version with the following spec.

### Core principles
- **Self-hosted first**: designed to run on a Raspberry Pi or home server via Docker Compose. No cloud dependency required.
- **Privacy by default**: all data stays local unless the user explicitly configures a remote LLM API.
- **LLM features are fully optional**: the app must be 100% usable with zero LLM configured — manual entry, barcode lookup, and search all work standalone. LLM only adds OCR-assist and meal/day analysis on top.
- **Open source ready**: clean structure, MIT or AGPL license (help me decide), docs from day one.

### Tech stack
- **Backend**: Python, FastAPI
- **Database**: SQLite (single file, easy backup, zero-admin)
- **Frontend**: Web app / PWA — plain React (Vite) or SvelteKit, your call on which is leaner for this scope. Must work well on mobile browser (installable PWA) and desktop.
- **Containerization**: Docker Compose for one-command self-hosting (`docker compose up`)
- **Auth**: simple single-user or small multi-user (household) auth — no need for enterprise-grade, just login + session/JWT

### Data sources for food database (v1)
- **Open Food Facts**: use their published bulk data export or REST API (barcode lookup) — do NOT scrape, they provide open data (ODbL license). https://world.openfoodfacts.org/data
- **USDA FoodData Central**: free API for generic/whole foods, public domain. https://fdc.nal.usda.gov/api-guide
- Local SQLite table for user-added custom products/recipes, always takes priority over external sources when present

### Core features for v1
1. **User & profile**: basic info (age, sex, weight, height, activity level, goal) used to calculate calorie/macro targets (Mifflin-St Jeor or similar formula)
2. **Food database search**: search local DB first, fall back to Open Food Facts / USDA API, cache results locally once fetched
3. **Barcode lookup**: manual barcode entry field for v1 (camera-based scanning can come later via browser barcode detection API)
4. **Manual food logging**: add food + quantity to a meal (breakfast/lunch/dinner/snack) for a given day
5. **Daily summary**: calories, macros (protein/fat/carbs), and available micronutrients vs. targets, shown as a dashboard
6. **Custom foods/recipes**: user can create their own food entries with full nutrition info
7. **Sync**: single backend = sync is inherent (all clients hit the same API); no separate sync logic needed for v1

### LLM features (optional, pluggable — build the interface but keep it decoupled)
- Define a simple backend-agnostic interface, e.g. `analyze_meal(nutrition_data, user_context) -> structured_insights` and `ocr_nutrition_label(image) -> structured_nutrition_data`
- Support pluggable providers configured via env vars: `none` (default), `anthropic` (Claude API), `openai`, `ollama` (local). Should be trivial to add more later.
- Feature 1 — **OCR nutrition label**: user photographs a product's nutrition table, image goes to whichever backend is configured (local vision model via Ollama, or an LLM API) and returns structured macros/micros to prefill a new food entry
- Feature 2 — **Meal review**: button on a logged meal to get LLM feedback (only visible/enabled if LLM is configured)
- Feature 3 — **Daily/weekly analysis**: LLM receives *pre-computed* nutrient gaps (compute deficits in code against RDA tables, don't make the LLM do the math) plus user profile, and returns structured JSON: `{summary, deficiencies: [...], suggestions: [{food, reason}]}`
- All LLM calls should fail gracefully and clearly indicate "LLM not configured" in the UI rather than breaking anything

### Project structure
```
/server
  /app
    /models        (SQLAlchemy models: User, Food, LogEntry, Recipe, ...)
    /routers        (FastAPI route modules)
    /services        (food_lookup, llm_adapter, nutrition_calc)
    /llm
      base.py        (abstract interface)
      anthropic.py
      ollama.py
      none.py
    main.py
  requirements.txt
  Dockerfile
/web
  (Vite/SvelteKit PWA app)
  Dockerfile
/docs
  self-hosting.md    (Pi + Docker Compose setup guide)
  architecture.md
docker-compose.yml
README.md
LICENSE
```

### What I want you to do first
1. Propose the DB schema (tables + key fields) for: users, foods (with source: local/off/usda), food_nutrients, log_entries, recipes, user_targets
2. Scaffold the FastAPI backend with the structure above, a working `/health` endpoint, and Open Food Facts barcode lookup working end-to-end (fetch by barcode → cache in local DB → return)
3. Scaffold the frontend with a basic food search + log-a-meal flow hitting the backend
4. Write the `docker-compose.yml` so the whole thing runs with one command
5. Stub the LLM adapter interface with a `none` provider as default and an `anthropic` provider as the first real implementation

Ask me clarifying questions if anything about scope, target users (just me vs multi-user household), or hosting environment is ambiguous before you start scaffolding.

---

## Notes for you (not part of the prompt)
- Decide MIT vs AGPL before publishing: AGPL is common for self-hosted OSS tools because it prevents someone from taking your code, hosting it as a closed SaaS, and not contributing back — worth considering given your SaaS-later idea.
- Keep the LLM adapter interface genuinely thin so adding Ollama/local support later isn't a rewrite.
- Once the barcode + manual logging loop works end-to-end, that's a good v1 milestone to actually start using daily — the LLM features can come after.
