# TOI — Commands and Concepts Reference

Quick reference for commands and concepts used during this project.

---

## Understanding the 3-Layer Enforcement System

Three layers work together to enforce rules (like auto-updating TOI.md and LESSONS_LEARNED.md):

| Layer | Scope | Survives? | Who reads it? |
|---|---|---|---|
| **The file** (TOI.md / LESSONS_LEARNED.md) | This project only | Yes, in git | You (human reference) |
| **CLAUDE.md** | This project only | Yes, in git | Claude — auto-loaded every session in this folder |
| **Memory** | Every project on this machine | Yes, in ~/.claude/ | Claude — loaded in every conversation regardless of folder |

- **The file** = the actual content you read and learn from.
- **CLAUDE.md** = instruction to Claude: apply this rule inside this project.
- **Memory** = backstop: apply this habit in ANY project that has these files.

If any layer is missing: no memory → habit breaks in new projects; no CLAUDE.md → less reliable enforcement; no file → nowhere to write.

---

## Git — Checking Repo State

## Working tree / staging state

```bash
git status          # what's staged, unstaged, untracked right now
git status -s        # same, compact form (M/A/?? per file)
```

## History

```bash
git log                          # full commit history, one entry per commit
git log --oneline                # compact, one line per commit
git log --oneline --graph --all  # visual branch/merge structure
git log -p -- <file>              # full diff history for one file
git show <commit>                 # full diff introduced by a specific commit
git show <commit> --stat          # just the file list + line counts for that commit
```

## What's actually inside a commit

```bash
git show --stat <commit>              # files changed + insertion/deletion counts
git show <commit> -- <file>           # just this file's diff in that commit
git ls-tree -r <commit> --name-only   # every file path tracked at that commit
```

## Diffing

```bash
git diff                 # unstaged changes vs. last commit
git diff --cached        # staged changes vs. last commit
git diff HEAD~1 HEAD      # diff between two commits
```

## Branches / remotes

```bash
git branch -a       # local + remote branches
git remote -v        # configured remotes
```

## Tracked vs. ignored files

```bash
git ls-files                    # every file git is currently tracking
git status --ignored             # shows what's being ignored (needs .gitignore)
git check-ignore -v <path>        # explains why a path is/isn't ignored
```

## kagglehub — downloading datasets

```python
import kagglehub, shutil, glob

# Download to kaggle's hidden cache (~/.cache/kagglehub/...)
cache_path = kagglehub.dataset_download("owner/dataset-slug")

# Find the CSV inside the cache and copy to your project
csv_file = glob.glob(f"{cache_path}/**/*.csv", recursive=True)[0]
shutil.copy(csv_file, "data/raw/ames_housing.csv")
```

```bash
# Check what kagglehub downloaded and where
ls ~/.cache/kagglehub/datasets/
```

## truststore — shared utility pattern (Zscaler fix)

```python
# src/utils.py — call once, import everywhere
import truststore
truststore.inject_into_ssl()   # must run before any HTTPS request

# every other file just does:
import src.utils   # fix applies automatically, Python runs it only once
```

## Python / pip / venv

```bash
python3 -m venv .venv                        # create isolated virtual environment
.venv/bin/pip install --upgrade pip          # upgrade pip inside the venv
.venv/bin/pip install <package>              # install into venv (not system Python)
.venv/bin/python3 -c "import <pkg>"          # test that a package is importable in venv
```

## TLS / SSL diagnostics

```bash
curl --version                               # shows which CA bundle curl uses by default
curl -v https://<host> 2>&1 | grep -i CAfile # which CA bundle this curl resolved to
curl --cacert <bundle.pem> https://<host>    # test a specific CA bundle
security find-certificate -a -c "Zscaler" /Library/Keychains/System.keychain  # check if a root CA is trusted in macOS keychain
```

## Environment variables / secrets

```bash
# Check if a variable is set in the current shell
echo $MLFLOW_TRACKING_URI

# Load .env file manually in shell (for testing)
export $(cat .env | grep -v '#' | xargs)

# Check what env vars a running Docker container sees
docker exec <container_name> env | grep MLFLOW
```

```python
# Standard pattern: works both locally and in Docker
from dotenv import load_dotenv
import os

load_dotenv()                                    # reads .env when running locally
uri = os.environ.get("MLFLOW_TRACKING_URI")     # Docker supplies it via env_file
```

```yaml
# docker-compose.yml — inject .env into every service
services:
  api:
    env_file:
      - .env
```

## Prefect — local server + scheduled flow

```bash
# Always run from project root
cd /Users/dvksuman/API

# Start Prefect server (keep this terminal open; override .env Docker URL)
PREFECT_API_URL=http://127.0.0.1:4200/api prefect server start --host 127.0.0.1 --port 4200

# In a second terminal: start the flow (registers deployment + acts as worker)
cd /Users/dvksuman/API
PREFECT_API_URL=http://127.0.0.1:4200/api python -m src.ops.pipeline_flow

# Trigger a manual run immediately (don't wait for schedule)
PREFECT_API_URL=http://127.0.0.1:4200/api prefect deployment run 'ames-housing-pipeline/ames-housing-2min'

# Check what deployments are registered
PREFECT_API_URL=http://127.0.0.1:4200/api prefect deployment ls

# Check flow run statuses (SCHEDULED / RUNNING / COMPLETED / FAILED)
PREFECT_API_URL=http://127.0.0.1:4200/api prefect flow-run ls

# Check Prefect's resolved config (shows which .env values it picked up)
prefect config view

# Check Prefect version
python -c "import prefect; print(prefect.__version__)"

# Open Prefect UI in browser
open http://127.0.0.1:4200
```

## Environment inspection

```bash
env | grep -i -E 'ssl|cert'                  # find SSL/cert-related environment variables
nslookup <host>                              # check DNS resolution (rules out DNS as cause)
ping -c 3 <host>                             # check raw connectivity (rules out network as cause)
```

## ML Training

```bash
# Run Group 6 training script (from project root)
python3 -m src.ml.train

# Quick check of encoded CSV shape and dtypes
python3 -c "import pandas as pd; df=pd.read_csv('data/processed/ames_housing_encoded.csv'); print(df.shape, df.dtypes.value_counts())"

# View model comparison table
cat output/model_comparison.csv

# View top features per model
cat output/feature_importance.csv | python3 -c "import sys,pandas as pd; df=pd.read_csv(sys.stdin); print(df.groupby('model').head(5).to_string())"
```

## MLflow

```bash
# Install mlflow
.venv/bin/pip install "mlflow>=2.10"

# Run the Group 7 tracking script (trains all 3 models + logs to MLflow + registers XGBoost)
cd /Users/dvksuman/API
.venv/bin/python3 -m src.ml.train_mlflow

# Start the MLflow UI (reads from SQLite backend)
.venv/bin/mlflow ui --backend-store-uri sqlite:///mlruns.db --port 5000
# Then open http://localhost:5000

# Check registered models via MLflow REST API
curl -s http://localhost:5000/api/2.0/mlflow/registered-models/list | python3 -m json.tool

# Load registered model by alias (for use in FastAPI Group 8)
# model_uri = "models:/AmesPricePredictor@production"
```
