# Taste profile
- Communicates in Spanish (Chilean business context) and expects responses, UI labels, and report text in Spanish. Confidence: 0.8
- Wants to be the single source of truth for domain data: keywords/entities should be exactly the list provided, without extra hardcoded or predefined values being added. Confidence: 0.6
- Approves validating configuration/credentials before use so failures surface as specific, actionable messages (what's missing, placeholder value, incomplete key) instead of generic errors or silent empty results. Confidence: 0.5
- Values deliverable artifacts: charts should be downloadable (PNG) and their underlying data exportable as CSV. Confidence: 0.6
- Targets Streamlit (Streamlit Cloud) as the runtime/deployment environment for the app. Confidence: 0.7
- Wants generated caches and runtime artifacts kept out of version control (`__pycache__/`, `*.pyc`, runtime cache/history dirs) via `.gitignore`. Confidence: 0.6
