# Movie Production Tracker Dashboard

Single-user Streamlit app for tracking a movie's production pipeline (Act → Scene),
including pipeline status, client/internal revision counts, and completion rollups.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub.
2. Go to https://share.streamlit.io → "New app".
3. Pick this repo, branch `main`, main file `app.py`.
4. Deploy.

## Note on data persistence
Data is saved to `tracker_data.json` next to `app.py`. On Streamlit Community Cloud,
the filesystem is **ephemeral** — it resets on redeploys, restarts, or after
inactivity puts the app to sleep. It's fine for local use; for cloud use you may
want to swap the storage layer for something durable later (e.g. a small hosted DB).
