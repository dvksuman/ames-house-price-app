# Lessons Learned — AIMLCZG549 Assignment I Build Log

Practical problems hit during development, what caused them, and how they were fixed.
Updated as new issues are discovered.

---

## LL-01: macOS blocked pip install ("externally managed environment")

**When**: Setting up the project Python environment (Group 1).

**What happened**: Running `pip3 install <package>` on the system Python failed with:
```
error: externally-managed-environment
× This environment is externally managed
```

**Why it happened**: macOS (from Sonoma onward) marks the system Python as "managed by the OS" under PEP 668. The intent is to stop user-installed packages from corrupting OS tools that also depend on Python. pip refuses to install into it without `--break-system-packages`, which is genuinely dangerous.

**Fix**: Create a project-level virtual environment first:
```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install <whatever>
```
Everything installed via this venv is isolated — can't break the OS and can't interfere with Anaconda or other Python installs on the same machine.

**Takeaway**: Always start a Python project with a venv, not the system or global Python. Add `.venv/` to `.gitignore` immediately so it doesn't get committed.

---

## LL-02: HTTPS requests failing — "unable to get local issuer certificate"

**When**: Group 2 (Data Ingestion) — trying to download the Ames Housing dataset from `jse.amstat.org`, `openml.org`, and `www.kaggle.com`.

**What happened**: Both `curl` and Python's `requests` library failed on these specific sites:
```
curl: (60) SSL certificate problem: unable to get local issuer certificate
SSLError: certificate verify failed: unable to get local issuer certificate
```
Meanwhile `github.com`, `pypi.org`, and `example.com` worked fine over HTTPS.

**Why it happened**: The machine sits behind **Zscaler**, a corporate TLS-inspection proxy. Zscaler acts as a "man in the middle" — it intercepts every HTTPS connection, inspects the traffic, and re-signs the certificate with its own Zscaler certificate before passing it to your machine. Tools that only trust the default public CA list (Mozilla's list, which ships with `curl`, Anaconda, and Python's `certifi` package) see an unfamiliar issuer and reject the connection.

Sites like `github.com` and `pypi.org` are typically whitelisted in Zscaler (bypassed, not inspected), which is why those worked.

**First discovery (curl CA path)**:
```bash
curl -v https://www.kaggle.com 2>&1 | grep CAfile
# Output: CAfile: /opt/anaconda3/ssl/cacert.pem
```
Anaconda shipped its own CA bundle, which doesn't include Zscaler's root.

**Confirmation that the system bundle had the fix**:
```bash
curl --cacert ~/.certs/system-ca-bundle.pem https://www.kaggle.com
# -> 200 OK
```
The `~/.certs/system-ca-bundle.pem` file (provisioned by MDM) includes the Zscaler root and curl trusted it.

**Deeper Python issue — Basic Constraints**: Even pointing Python's `requests` at the same bundle via `REQUESTS_CA_BUNDLE` failed with a different error:
```
certificate verify failed: Basic Constraints of CA cert not marked critical
```
Zscaler's intermediate certificate is technically non-compliant with RFC 5280 (it doesn't mark the `basicConstraints` extension as "critical", which the spec says it must be for a CA cert). Python's `ssl` module enforces this strictly. `curl` doesn't.

**Final fix — `truststore` package**:
```bash
pip install truststore
```
```python
import truststore
truststore.inject_into_ssl()   # call this before any requests
import requests
r = requests.get('https://www.kaggle.com')
```
`truststore` makes Python validate certificates using the **macOS Keychain** (the OS's own trust store) instead of `certifi`. The Keychain already trusts the Zscaler root (installed by MDM), and macOS's native TLS verifier is more lenient about the RFC 5280 technicality that Python rejects.

**Takeaway**: When HTTPS works in a browser but fails in Python/curl on a corporate machine, suspect a TLS-inspection proxy (Zscaler, Palo Alto, BlueCoat). The fix is not to disable certificate verification (`verify=False`) — that removes all TLS security. The correct fix is to point your tools at the trust root the OS already uses.

---

## LL-03: GitHub code search requires authentication (401)

**When**: Searching GitHub for an alternative CSV mirror of the Ames Housing dataset.

**What happened**: 
```bash
curl "https://api.github.com/search/code?q=filename:AmesHousing.csv"
# -> 401 Requires authentication
```

**Why it happened**: GitHub deprecated unauthenticated code search in 2023. The `/search/code` endpoint now requires a Personal Access Token (PAT) in the `Authorization` header.

**Workaround**: The `/search/repositories` and `/repos/{owner}/{repo}/contents/{path}` endpoints still work unauthenticated for public repositories. Used those instead to browse candidate repos manually.

**Takeaway**: The GitHub API has different auth requirements per endpoint. Repository search and content listing are public; code search is not. When writing code that queries GitHub, use a PAT (stored as an env var, never hardcoded) to avoid hitting these restrictions.

---

## LL-04: topepo/AmesHousing GitHub repo has no CSV — only R binary files

**When**: Searching for a CSV mirror of the full Ames Housing dataset.

**What happened**: `topepo/AmesHousing` is the highest-starred R package that mirrors Dean De Cock's original Ames data. But its `data/` directory only contains `.rda` (R Data Archive) binary files — not CSVs:
```
ames_geo.rda, ames_new.rda, ames_raw.rda, hood_levels.rda ...
```

**Why it happened**: The R ecosystem stores package datasets as serialized R objects (`.rda`), not as CSVs. To use them in Python you'd need an R installation and `rpy2`, or a separate conversion step. Not suitable for a Python-only pipeline.

**Lesson**: When hunting for dataset mirrors, filter early by file extension — a popular repo with the right name is useless if the format doesn't match your stack.

**Resolution**: Turned out not to be necessary — after fixing the Zscaler TLS issue (LL-02), the original source URL (`jse.amstat.org/v19n3/decock/AmesHousing.txt`) became reachable directly. It returned 2,930 rows × 82 columns — the full canonical dataset. No mirror needed.

---

## LL-05: Kaggle credentials not provisioned on the development machine

**When**: Group 2 (Data Ingestion) — trying `kagglehub` as the primary download path.

**What happened**: No `~/.kaggle/kaggle.json` exists. `kagglehub` (and the Kaggle CLI) both look for this file and fail immediately without it:
```
ls: /Users/dvksuman/.kaggle/kaggle.json: No such file or directory
```

**Why it happened**: Kaggle requires API credentials even for public datasets. The token must be generated manually at kaggle.com (account settings → API → Create New Token), then placed at `~/.kaggle/kaggle.json` with `chmod 600` permissions (Kaggle refuses to use it otherwise).

**Fix (in progress)**: Generate and place the token. Steps:
1. Log in at kaggle.com → Settings → API → Create New Token → downloads `kaggle.json`
2. `mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json`
3. `chmod 600 ~/.kaggle/kaggle.json`

**Design implication**: The ingestion script is structured with Kaggle as primary and `jse.amstat.org` as fallback — so it degrades gracefully when credentials aren't set up, which is the right pattern for a pipeline that may run in containers or CI where credentials may or may not be mounted.

**Takeaway**: Any external API credential (Kaggle, HuggingFace, Weights & Biases, etc.) needs a provisioning step before it can be used. Don't assume credentials exist — check early, fail with a clear message, and always have a fallback that doesn't require auth.

---

## LL-06: Secrets and config must never be hardcoded — use .env + Docker env_file

**When**: Setting up environment configuration before writing any service code (pre-Group 2).

**What happened**: Needed to store config values (MLflow URI, Prefect API URL) and credentials (Kaggle token) that would be used both in local Python scripts and inside Docker containers. Hardcoding them in source files would mean they'd end up in git and be different between environments.

**Why it matters**: Hardcoded secrets in source code get committed to git and are then visible to anyone with repo access — permanently, even after deletion (git history preserves them). Config that differs between environments (local vs Docker) breaks when the code moves.

**The correct pattern — two files working together**:

`project/.env` (never committed, in .gitignore):
```
MLFLOW_TRACKING_URI=sqlite:///mlruns/mlflow.db
PREFECT_API_URL=http://prefect:4200/api
```

`docker-compose.yml` (committed, safe — contains no values):
```yaml
services:
  api:
    env_file:
      - .env
```

Python code (committed, safe — reads from environment, not from file directly):
```python
from dotenv import load_dotenv
import os
load_dotenv()  # for local runs outside Docker
uri = os.environ.get("MLFLOW_TRACKING_URI")
```

**How it works per environment**:
- Local Python → `load_dotenv()` reads `.env` file
- Docker container → `docker-compose.yml` injects `.env` values at startup
- Same code, same variable name, different supplier

**Fix**: Created `.env` with all config values, added `python-dotenv` to `requirements.txt`, `.env` already excluded by `.gitignore`.

**Takeaway**: This is the "12-factor app" principle — config lives in the environment, not in the code. Write code that reads `os.environ.get(...)` and let the deployment context (local `.env` or Docker `env_file`) supply the actual values. Never hardcode URLs, ports, or credentials.

---

## LL-07: Shared utility for truststore — don't repeat the fix in every file

**When**: Designing the ingestion module (pre-implementation, Group 2 explore).

**The problem**: `truststore.inject_into_ssl()` must be called before any HTTPS request on this machine (Zscaler fix — see LL-02). Multiple files make HTTPS calls:
- `src/data/ingest.py` — downloads dataset
- `src/ml/train.py` — talks to MLflow server
- `src/api/main.py` — calls MLflow + Prefect REST APIs

If we write `truststore.inject_into_ssl()` in each file separately, we will eventually forget one and get a confusing SSL error that seems random.

**The correct pattern — one shared utility**:
```
src/utils.py
    import truststore
    truststore.inject_into_ssl()   ← called once here

src/data/ingest.py  → import src.utils  → fix applies automatically
src/ml/train.py     → import src.utils  → fix applies automatically
src/api/main.py     → import src.utils  → fix applies automatically
```

**Why this works**: Python only executes a module's top-level code once, the first time it is imported. Every subsequent `import src.utils` reuses the already-loaded module — so `inject_into_ssl()` runs exactly once per Python process, which is all that's needed.

**Takeaway**: Any "setup once, needed everywhere" fix (SSL injection, logging config, env loading) belongs in a shared utility module — not copy-pasted into every file that needs it.

---

## LL-08: kagglehub downloads to a hidden cache — you must copy the file yourself

**When**: Designing Kaggle ingestion (pre-implementation, Group 2 explore).

**How kagglehub works**:
```python
import kagglehub
path = kagglehub.dataset_download("owner/dataset-name")
# path → ~/.cache/kagglehub/datasets/owner/dataset-name/versions/1/
```

`kagglehub` saves the file to its own hidden cache folder (`~/.cache/kagglehub/...`), not to a path you specify. Your pipeline then needs to:
1. Find the downloaded file inside that cache path
2. Copy it to your project's `data/raw/` folder

```python
import shutil, glob
cache_path = kagglehub.dataset_download("owner/dataset-name")
csv_file = glob.glob(f"{cache_path}/**/*.csv", recursive=True)[0]
shutil.copy(csv_file, "data/raw/ames_housing.csv")
```

**The jse.amstat.org fallback is simpler** — we stream directly to `data/raw/`:
```python
r = requests.get(URL, stream=True)
with open("data/raw/ames_housing.csv", "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)
```

**Verified Kaggle slug**: `marcopale/housing` → file `AmesHousing.csv` → 2,930 rows × 82 columns, SalePrice present. Confirmed correct. The other candidates (`prevek18/ames-housing-dataset`, `shashanknecrothapa/ames-housing-dataset`) are likely the 1,460-row Kaggle competition split — do not use them.

**Takeaway**: When using `kagglehub`, always check the cache path returned, glob for the actual file inside it, then copy to your project. Never assume the file lands where you want it.

---

## LL-09: pandas reads "None" strings back as NaN from CSV

**When**: Group 3 preprocessing verification — processed CSV showed 15,066 nulls after imputation that had already been filled.

**What happened**: We filled semantic-NA categorical columns with the string `"None"` (e.g. Pool QC → "None" means "no pool"). The values were written correctly to CSV. But when reading the file back with `pd.read_csv()`, pandas converted every `"None"` back to `NaN` because `"None"` is in pandas' built-in NA string list (`na_values` defaults).

**Why it happened**: pandas `read_csv()` treats many strings as NA by default: `""`, `"NA"`, `"NaN"`, `"None"`, `"null"`, `"N/A"` and others. It does this silently — no warning, the column just has NaN where you expect a string.

**Fix**: Added `read_processed_csv()` to `src/utils.py` which calls `pd.read_csv(path, keep_default_na=False, na_values=[""])`. This disables all built-in NA string detection and only treats empty cells as NaN. Every downstream script (EDA, training, API) must use this function instead of `pd.read_csv()` directly when reading processed CSV files.

**Takeaway**: Never use `pd.read_csv()` directly on a CSV that contains `"None"` as a real category value. Use `keep_default_na=False, na_values=[""]` or a shared reader utility.

---

*Last updated: 2026-07-10*
