# Filter my Numbers

Initial local MVP for bulk phone-number format validation. Upload a UTF-8 CSV (first column) or TXT (one number per line), up to 5,000 entries and 2 MB, and download a CSV with numbering-plan validity, E.164 formatting, region, original carrier allocation when available, and number type. It does not establish reachability or app registration. No database, accounts, payments, persistent job history, or public deployment are included yet.

## Local run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Test with a CSV of numbers in international format, or enter a two-letter region for national-format numbers. The response directly downloads the results CSV; no results page or task list is implemented yet. Do not deploy publicly without authentication, rate limits, privacy policy, and production testing.
