# Unified VAPT Agent

Streamlit-based VAPT assistant (Python, SQLite, Nmap, OWASP ZAP, Nikto, OpenAI). Specifications are in the numbered `0x_*.md` / `1x_*.md` files.

**Status:** Phase 1-4B implemented (Foundation, Database persistence, Scope & Operation validation, Nmap integration, OWASP ZAP integration).

## Install

```powershell
python -m pip install -r requirements.txt
```

## Configure

Create/edit `.env` (never committed):

```
OPENAI_API_KEY=your-key
# optional: OPENAI_MODEL, DATABASE_PATH, SCANNER_OUTPUT_DIR, REPORTS_DIR, LOG_LEVEL
```

### Scope (required before any target can be accepted)

Targets are rejected unless explicitly allowlisted (comma-separated, no wildcards/CIDR):

```
AUTHORIZED_TARGETS=127.0.0.1:8080,lab.example.test,http://dvwa.test
EXCLUDED_TARGETS=admin.lab.example.test      # optional, wins over authorized
ALLOWED_OPERATIONS=zap.passive_scan,nmap.service_scan   # optional; default: all registry operations
```

An entry without a port covers any port on that host; an entry with a port covers only that port.

### Nmap (optional settings)

```
NMAP_PATH=C:\Program Files (x86)\Nmap\nmap.exe   # default: found on PATH
NMAP_TIMEOUT_SECONDS=300
```

The UI runs `nmap.service_scan` (service/version detection, top 100 ports unless `ports` is given) only when you click **Run service scan**, and only for authorized targets.

### OWASP ZAP (optional settings)

```
ZAP_API_URL=http://127.0.0.1:8090   # default: http://127.0.0.1:8090 (loopback only)
ZAP_API_KEY=                        # optional API key for ZAP daemon
ZAP_TIMEOUT_SECONDS=300
```

The UI runs `zap.passive_scan` (bounded passive inspection: sends a single request to the authorized target URL, waits for ZAP's passive scanner queue to drain, and retrieves normalized alerts). No spider, no crawler, no active attack payloads. Runs only when you click **Run passive scan**, and only for authorized targets.

## Run

```powershell
python -m streamlit run app.py
```

## Test

```powershell
python -m pytest
```

