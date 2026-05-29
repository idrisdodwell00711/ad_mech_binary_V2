# Cogitator-Vox MK.IV — web data-shrine

FSK text↔audio transcoder (Adeptus Mechanicus themed), as a Flask web app
ready to deploy on Render.

## Files
- `app.py`            — Flask routes (`/encode`, `/decode`, `/healthz`)
- `codec.py`          — the BFSK codec core (pure stdlib, no display needed)
- `templates/index.html` — themed front-end (blood-red + brass on iron)
- `requirements.txt`  — Flask + gunicorn
- `render.yaml`       — Render blueprint (optional; you can also configure in the dashboard)

## Run locally
    pip install -r requirements.txt
    python app.py            # http://localhost:5000



## Notes
- Upload cap is 25 MB (`MAX_CONTENT_LENGTH` in `app.py`).
- Codec params (`FREQ_ZERO`, `FREQ_ONE`, `BIT_DURATION`) live in `codec.py`;
  encode and decode read the same values, so they stay in sync. Currently
  2 kHz / 6 kHz, 0.025 s per bit.
