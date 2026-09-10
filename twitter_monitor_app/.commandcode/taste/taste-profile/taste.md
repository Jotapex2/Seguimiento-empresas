# Taste profile
- Communicates in Spanish (Chilean business context) and expects responses, UI labels, and report text in Spanish. Confidence: 0.8
- Wants to be the single source of truth for domain data: keywords/entities should be exactly the list provided, without extra hardcoded or predefined values being added. Confidence: 0.6
- Approves validating configuration/credentials before use so failures surface as specific, actionable messages (what's missing, placeholder value, incomplete key) instead of generic errors or silent empty results. Confidence: 0.5
- Values deliverable artifacts: charts should be downloadable (PNG) and their underlying data exportable as CSV. Confidence: 0.6
- Expects visualization encodings to reflect magnitude — e.g., word-cloud font size proportional to the number of mentions/frequency. Confidence: 0.5
- Targets Streamlit (Streamlit Cloud) as the runtime/deployment environment for the app. Confidence: 0.7
- Expects sentiment analysis to measure attitude toward the mentioned entity, not the theme: sector/industry vocabulary (mining, automotive, energy, etc.) and generic corporate terms must not be read as negative or appear as sentiment signals. Confidence: 0.5
- Wants generated caches and runtime artifacts kept out of version control (`__pycache__/`, `*.pyc`, runtime cache/history dirs) via `.gitignore`. Confidence: 0.6
