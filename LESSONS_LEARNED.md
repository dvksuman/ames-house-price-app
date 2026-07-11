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

## LL-10: matplotlib needs Agg backend when there is no display

**When**: Group 4 EDA — saving plots to PNG files on a machine without a GUI display open.

**What happened**: matplotlib by default tries to open a GUI window to show the chart. On a server or when running in a terminal without a display, this throws an error or hangs.

**Fix**: Set `matplotlib.use("Agg")` before importing `matplotlib.pyplot`. The Agg backend renders charts entirely in memory and writes them to image files without needing a screen.

**Takeaway**: Always set `matplotlib.use("Agg")` at the top of any script that saves plots to files. Must be called before `import matplotlib.pyplot as plt`.

---

## LL-11: Ordinal map key mismatch causes silent NaN in encoded dataset

**When**: Integration check between Group 3 (preprocessing) and Group 4 (EDA encoding).

**What happened**: The encoded dataset had 12 NaN values in the `Fence` column after ordinal encoding, even though the processed dataset had 0 nulls.

**Why it happened**: Our `OTHER_ORDINAL` map for `Fence` used the key `"MnWo"` (Minimum Wood — taken from De Cock's data dictionary). But the actual data contains `"MnWw"` (Minimum Wire). When `pd.Series.map()` encounters a value not in the mapping dict, it returns NaN silently — no warning or error.

**Fix**: Replaced `"MnWo": 1` with `"MnWw": 1` in the Fence mapping in `src/eda/eda.py`.

**Takeaway**: After any ordinal encoding step, always check `df.isnull().sum()` on the output. A value in the data that doesn't appear in your mapping map becomes NaN silently. When ordinal maps are hand-written from a data dictionary, verify actual unique values in the data first — the dictionary and the data can disagree.

---

## LL-12: Prefect UI shows wrong API URL when .env has a Docker hostname

**When**: Group 5, first attempt to view the Prefect UI in a browser.

**What happened**: Opening `http://127.0.0.1:4200` showed "Can't connect to Server API at http://prefect:4200/api." The server was running, but the UI was trying to reach the Docker service hostname instead of localhost.

**Why it happened**: Prefect 3.x reads `.env` files in the current directory automatically (not just via python-dotenv). Our `.env` has `PREFECT_API_URL=http://prefect:4200/api` for Docker Compose. The Prefect server picks this up and tells the UI frontend to use that URL.

**Fix**: Start the server with the env var explicitly overridden in the shell:
```bash
PREFECT_API_URL=http://127.0.0.1:4200/api prefect server start --host 127.0.0.1 --port 4200
```
The same override is needed when running the serve process:
```bash
PREFECT_API_URL=http://127.0.0.1:4200/api python -m src.ops.pipeline_flow
```

**Takeaway**: A `.env` file with Docker service names breaks local Prefect server + UI. Always override `PREFECT_API_URL` in the shell when running locally. The Docker value in `.env` stays correct for docker-compose; the shell override handles local dev.

---

## LL-13: `python -m src.ops.pipeline_flow` fails if not run from project root

**When**: Group 5, restarting the serve process after killing the old one.

**What happened**: `ModuleNotFoundError: No module named 'src'` when running `python -m src.ops.pipeline_flow` from a different directory.

**Why it happened**: The `src` package is resolved relative to the current working directory. Running from any directory other than `/Users/dvksuman/API` means Python can't find the `src` package.

**Fix**: Always `cd /Users/dvksuman/API` first, or use an absolute path with the `-m` flag. The flow file also sets `os.chdir(PROJECT_ROOT)` at module level as an extra safety net for relative file paths inside tasks.

**Takeaway**: For any project using `python -m src.something`, the CWD must be the project root. Keep a `cd /Users/dvksuman/API` at the start of any Prefect-related command in TOI.md.

---

*Last updated: 2026-07-10*

---

## LL-09: Bool columns in one-hot CSV must be cast to int before sklearn

**When**: Group 6, Task 6.1  
**What happened**: `ames_housing_encoded.csv` stores one-hot encoded columns as Python `True`/`False`. Pandas reads them as `object` dtype (not numeric), which causes sklearn to raise a `ValueError: could not convert string to float`.  
**Why it happened**: Python's `bool` type serialises as `True`/`False` strings in CSV. Pandas infers object dtype for those strings unless you cast explicitly.  
**Fix**: `df[df.select_dtypes(include="bool").columns] = df[bool_cols].astype(int)` right after loading.  
**Takeaway**: Always check `df.dtypes.value_counts()` after loading an encoded CSV. Cast bools to int before any sklearn call.

---

## LL-10: Ridge/Lasso need StandardScaler; XGBoost does not

**When**: Group 6, Task 6.2–6.3  
**What happened**: Fitting the scaler on `X_train` then transforming `X_test` (not refitting) is the correct pattern. Scaling `X_test` with the train scaler avoids data leakage.  
**Why it happened**: If you fit the scaler on all data before the split, test-set statistics leak into training — inflating reported performance.  
**Fix**: `scaler.fit_transform(X_train)` → `scaler.transform(X_test)`. Never `fit` on test data.  
**Takeaway**: Tree models are scale-invariant; linear models with regularisation are not. Keep separate scaled and unscaled copies of X_train/X_test.

---

## LL-07 — MLflow 3.x: `artifact_path` deprecated, use `name`

**When**: Group 7, task 7.2

**What happened**: `mlflow.sklearn.log_model(model, artifact_path="model")` produced a `FutureWarning` in mlflow 3.14 — `artifact_path` is deprecated.

**Why**: MLflow 3.x unified the `log_model` API. The `artifact_path` kwarg was renamed to `name`.

**Fix**: Change `artifact_path="model"` → `name="model"` in all `log_model` calls.

**Takeaway**: Always check the installed mlflow version (`pip show mlflow`) before referencing old tutorials — the API changed significantly between 2.x and 3.x.

---

## LL-08 — MLflow 2.9+ stages deprecated; use aliases for Model Registry

**When**: Group 7, task 7.3

**What happened**: The old `client.transition_model_version_stage(..., stage="Production")` API shows a deprecation warning in mlflow 2.9+ and will be removed.

**Why**: MLflow replaced fixed stages (None/Staging/Production/Archived) with free-form aliases.

**Fix**: Use `client.set_registered_model_alias(name, "production", version)` instead.

**Takeaway**: For mlflow>=2.9, always use aliases for labelling model versions. In Group 8 (FastAPI), load the registered model with `models:/AmesPricePredictor@production` URI.

---

---

## LL-08 — SalePrice data leakage in XGBoost training

**When**: Group 8 (API Layer), 2026-07-11

**What happened**: The MLflow training script (`train_mlflow.py`) dropped only `LogSalePrice` from the feature set but left `SalePrice` in. XGBoost trained on `SalePrice` as a feature (with R²=0.994 — suspiciously perfect). When `/predict` was called without `SalePrice` in the payload, XGBoost raised `ValueError: feature_names mismatch`.

**Why it happened**: `X = df.drop(columns=[TARGET])` only dropped `LogSalePrice`. `SalePrice` and `is_test` were still present.

**Fix**: Changed the drop to `DROP_COLS = [c for c in [TARGET, "SalePrice", "is_test"] if c in df.columns]`. Re-ran training — model version 2 now uses 213 legitimate features. Real R² is 0.929 (not 0.994).

**Takeaway**: Always check what columns are in `X` after the drop — print `X.columns.tolist()` or assert `"SalePrice" not in X.columns` before fitting any model.

---

## LL-09 — XGBoost feature column order mismatch

**When**: Group 8 (API Layer), 2026-07-11

**What happened**: Even after fixing the leakage, `/predict` still failed. The DataFrame built from the Pydantic payload had columns in alphabetical (Pydantic field declaration) order, not the order the model was trained on.

**Why it happened**: XGBoost validates feature names AND order. A different column order raises `ValueError: feature_names mismatch`.

**Fix**: Reorder the input DataFrame before calling `model.predict()`:
```python
model_col_order = model._model_impl.xgb_model.get_booster().feature_names
input_df = input_df[model_col_order]
```

**Takeaway**: Always reorder input columns to match training order when serving XGBoost via MLflow pyfunc.

---

## LL-10 — Pydantic response model version field type mismatch

**When**: Group 8 (API Layer), 2026-07-11

**What happened**: `/predict` returned HTTP 500 with `pydantic_core.ValidationError`. The `PredictResponse.model_version` field was declared `str` but `mv.version` from MLflow is an integer.

**Fix**: Cast to string at assignment: `app.state.model_version = str(mv.version)`.

**Takeaway**: MLflow's `model_version.version` is an int. Always cast to `str` when storing for use in a Pydantic `str` field.

---

## LL-11 — Prefect REST API endpoint for listing deployments

**When**: Group 8 (API Layer), 2026-07-11

**What happened**: `GET /api/deployments` returned 307 redirect to `/api/deployments/`, which then returned 405 Method Not Allowed. The correct Prefect 3.x endpoint for listing deployments is `POST /api/deployments/filter` with a JSON filter body.

**Fix**: Changed from `httpx.get(".../deployments")` to `httpx.post(".../deployments/filter", json={...})`.

**Takeaway**: Prefect 3.x REST API uses POST + filter body for collection queries (deployments, flow-runs, flows). Never assume GET for listing; check the Prefect API docs or test with curl first.

---

## LL-12 — MLflow experiment name differs from registered model name

**When**: Group 8 (API Layer), 2026-07-11

**What happened**: `client.get_experiment_by_name("AmesPricePredictor")` returned `None`. The experiment was registered as `ames-housing-price-prediction` (set in `train_mlflow.py`), which is different from the registered model name `AmesPricePredictor`.

**Fix**: Added a separate constant `EXPERIMENT_NAME = "ames-housing-price-prediction"` and used it in the experiment lookup.

**Takeaway**: MLflow experiment name and registered model name are independent. Always look up the actual experiment name with `client.search_experiments()` before hardcoding it in API code.

---

*Last updated: 2026-07-11*

## LL-13 — Port already in use when starting FastAPI

**When**: Group 9 (Dashboard), 2026-07-11

**What happened**: `uvicorn` failed with `[Errno 48] address already in use` on port 8000. A previous uvicorn process (PID 16981) was still running in the background.

**Fix**: `lsof -i :8000` to find the PID, then `kill <PID>`, then restart uvicorn.

**Takeaway**: Always check `lsof -i :<port>` before starting a server. On Mac, port conflicts show `[Errno 48]` not `[Errno 98]` (Linux).

---

## LL-14 — EDA plots were in output/plots/, not output/eda/

**When**: Group 9 (Dashboard), 2026-07-11

**What happened**: The EDA FastAPI endpoint was initially coded to read from `output/eda/`. The actual path written by the EDA pipeline is `output/plots/`.

**Fix**: Updated `EDA_PLOTS_DIR` in `main.py` to point to `output/plots/`.

**Takeaway**: Always verify actual output paths with `ls output/` before hardcoding them in a new endpoint. Don't assume the path from memory.

---

*Last updated: 2026-07-11*
