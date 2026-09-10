# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Streamlit monitoring app in `twitter_monitor_app/`.

- `app.py` is the Streamlit entry point and coordinates UI flow.
- `components/` contains reusable UI sections: filters, KPIs, charts, tables, and taxonomy editing.
- `services/` contains API access, data collection, classification, scoring, exporting, email delivery, and runtime storage.
- `config/settings.py` loads environment-driven app configuration.
- `data/keywords.py` defines the default monitoring taxonomy.
- `utils/` contains shared text and datetime helpers.
- Runtime files are written under `twitter_monitor_app/data/runtime/`; treat them as generated local state.

## Build, Test, and Development Commands

Run commands from `twitter_monitor_app/` unless noted otherwise.

```bash
pip install -r requirements.txt
```

Installs the app dependencies.

```bash
streamlit run app.py
```

Starts the local dashboard. Simulation mode works without API credentials.

```bash
python google_social_monitor.py --platform linkedin --keywords Andess "agua potable"
```

Runs the Google/Serper monitor from the CLI.

## Coding Style & Naming Conventions

Use Python 3.10+ with 4-space indentation and type hints where practical. Keep UI in `components/`, business logic in `services/`, and shared helpers in `utils/`.

Use `snake_case` for functions, variables, and modules. Use `PascalCase` for classes and exceptions, such as `TwitterClient` and `TwitterApiError`. Keep UI labels in Spanish.

## Testing Guidelines

No automated test framework is configured yet. When adding tests, prefer `pytest` and place files under `tests/` with names like `test_classifier.py`.

Prioritize tests for pure logic first:

- taxonomy matching and text normalization
- Chile context/origin detection
- relevance and risk scoring
- query construction
- export frame transformations

Before submitting, run Streamlit in simulation mode and verify the dashboard, filters, exports, and any touched Google/X flow.

## Commit & Pull Request Guidelines

The existing history uses short messages such as `updates`, `up`, and `Mejoras en la UI`. Prefer descriptive imperative messages:

```text
Add taxonomy editor export
Fix Google result deduplication
Improve X API cache handling
```

Pull requests should include a summary, affected modules, manual validation steps, and screenshots for UI changes. Link issues when available and mention new environment variables.

## Security & Configuration Tips

Do not commit real secrets. Keep credentials in `.env` and placeholders in `.env.example`. Relevant variables include `TWITTERAPI_IO_KEY`, `SERPER_API_KEY`, `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `EMAIL_FROM`.
