"""DragonFlow FastAPI Backend - serves the React frontend and provides data APIs."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Project root is two levels up from app/api/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

app = FastAPI(title="DragonFlow API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class DownloadStartRequest(BaseModel):
    startDate: str = "2026-01-01"
    endDate: str = "2026-05-31"
    indexCode: str = "932000"
    adjust: str = "qfq"
    force: bool = False
    sleep: float = 0.3
    skipFundamental: bool = False
    limit: int = 0


# ---------------------------------------------------------------------------
# In-memory cache (simulated Redis) - loaded at startup
# ---------------------------------------------------------------------------
_cache: dict[str, Any] = {}


def _load_cache() -> None:
    """Load frequently-used data into memory at server startup."""
    import pandas as pd

    # --- Stock Info ---
    stock_info_path = PROJECT_ROOT.joinpath("data", "processed", "stock_info_csi2000_latest.parquet")
    if not stock_info_path.exists():
        stock_info_path = stock_info_path.with_suffix(".csv")
    if stock_info_path.exists():
        if stock_info_path.suffix == ".parquet":
            df = pd.read_parquet(stock_info_path)
        else:
            df = pd.read_csv(stock_info_path, dtype=str, encoding="utf-8-sig")
        _cache["stock_info"] = df.fillna("").to_dict(orient="records")

        # Pre-compute industry distribution
        if "industry" in df.columns:
            counts = df["industry"].value_counts().to_dict()
            _cache["industry_distribution"] = [
                {"name": k, "value": int(v)} for k, v in counts.items() if k and k != ""
            ]
    else:
        _cache["stock_info"] = []
        _cache["industry_distribution"] = []

    # --- Constituents ---
    cons_path = PROJECT_ROOT.joinpath("data", "raw", "csi2000", "constituents_932000_latest.csv")
    if cons_path.exists():
        df = pd.read_csv(cons_path, dtype=str, encoding="utf-8-sig")
        _cache["constituents"] = df.fillna("").to_dict(orient="records")
    else:
        _cache["constituents"] = []

    # --- Index Daily (skip from cache - filter on demand) ---
    _cache["index_daily"] = []

    # --- Stock Daily (skip from cache - too large) ---
    _cache["stock_daily"] = []

    print(f"[Cache] Loaded: stock_info={len(_cache.get('stock_info', []))}, "
          f"industry_dist={len(_cache.get('industry_distribution', []))}, "
          f"constituents={len(_cache.get('constituents', []))}")


# Load cache immediately when module is imported
_load_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def resolve_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def read_csv_safe(path: Path, nrows: int | None = None) -> list[dict]:
    import pandas as pd
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", nrows=nrows)
        return df.fillna("").to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取CSV失败: {e}")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "project": "DragonFlow"}


# --- Data Stats ---
@app.get("/api/data/stats")
def data_stats() -> dict:
    """Return overview statistics about downloaded data."""
    stats = {
        "nConstituents": 0,
        "nStockDaily": 0,
        "nIndexDaily": 0,
        "nStockInfo": 0,
        "nFundamental": 0,
        "coverageRatio": 0.0,
        "dateRange": {"start": "2026-01-01", "end": "2026-05-31"},
    }

    # Constituents
    cons_path = resolve_path("data", "raw", "csi2000", "constituents_932000_latest.csv")
    if cons_path.exists():
        import pandas as pd
        df = pd.read_csv(cons_path, dtype=str, encoding="utf-8-sig")
        stats["nConstituents"] = len(df)

    # Stock daily merged
    sd_path = resolve_path("data", "processed", "stock_daily_csi2000_qfq_20260101_20260531.parquet")
    if not sd_path.exists():
        sd_path = sd_path.with_suffix(".csv")
    if sd_path.exists():
        import pandas as pd
        if sd_path.suffix == ".parquet":
            df = pd.read_parquet(sd_path)
        else:
            df = pd.read_csv(sd_path, dtype=str, encoding="utf-8-sig")
        stats["nStockDaily"] = len(df)

    # Index daily
    idx_path = resolve_path("data", "raw", "csi2000", "index_daily_932000_20260101_20260531.csv")
    if idx_path.exists():
        import pandas as pd
        df = pd.read_csv(idx_path, dtype=str, encoding="utf-8-sig")
        stats["nIndexDaily"] = len(df)

    # Coverage report
    cov_path = resolve_path("data", "processed", "data_coverage_report.csv")
    if cov_path.exists():
        import pandas as pd
        df = pd.read_csv(cov_path, dtype=str, encoding="utf-8-sig")
        if "download_success" in df.columns:
            success = df["download_success"].astype(str).str.lower().isin(["true", "1", "yes"])
            stats["coverageRatio"] = round(success.mean() * 100, 1)

    return {"success": True, "data": stats}


# --- Constituents ---
@app.get("/api/data/constituents")
def get_constituents() -> dict:
    data = _cache.get("constituents", [])
    if not data:
        path = resolve_path("data", "raw", "csi2000", "constituents_932000_latest.csv")
        data = read_csv_safe(path)
    return {"success": True, "data": data}


# --- Stock Daily ---
@app.get("/api/data/stock-daily")
def get_stock_daily(
    stockCode: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    limit: int = 100,
) -> dict:
    import pandas as pd
    path = resolve_path("data", "processed", "stock_daily_csi2000_qfq_20260101_20260531.parquet")
    if not path.exists():
        path = path.with_suffix(".csv")
    if not path.exists():
        return {"success": True, "data": []}

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")

    if stockCode:
        df = df[df["stock_code"] == stockCode]
    if startDate and "date" in df.columns:
        df = df[df["date"] >= startDate]
    if endDate and "date" in df.columns:
        df = df[df["date"] <= endDate]

    df = df.head(limit)
    return {"success": True, "data": df.fillna("").to_dict(orient="records")}


# --- Index Daily ---
@app.get("/api/data/index-daily")
def get_index_daily(
    indexCode: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
) -> dict:
    import pandas as pd
    path = resolve_path("data", "raw", "csi2000", "index_daily_932000_20260101_20260531.csv")
    if not path.exists():
        return {"success": True, "data": []}

    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")

    if startDate and "date" in df.columns:
        df = df[df["date"] >= startDate]
    if endDate and "date" in df.columns:
        df = df[df["date"] <= endDate]

    return {"success": True, "data": df.fillna("").to_dict(orient="records")}


# --- Stock Info ---
@app.get("/api/data/stock-info")
def get_stock_info() -> dict:
    data = _cache.get("stock_info", [])
    if not data:
        path = resolve_path("data", "processed", "stock_info_csi2000_latest.parquet")
        if not path.exists():
            path = path.with_suffix(".csv")
        if not path.exists():
            return {"success": True, "data": []}

        import pandas as pd
        if path.suffix == ".parquet":
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        data = df.fillna("").to_dict(orient="records")
    return {"success": True, "data": data}


# --- Industry Distribution ---
@app.get("/api/data/industry-distribution")
def get_industry_distribution() -> dict:
    data = _cache.get("industry_distribution", [])
    return {"success": True, "data": data}


# --- Coverage Report ---
@app.get("/api/data/coverage")
def get_coverage() -> dict:
    path = resolve_path("data", "processed", "data_coverage_report.csv")
    data = read_csv_safe(path, nrows=100)
    return {"success": True, "data": data}


# --- Download Manifest ---
@app.get("/api/download/manifest")
def get_manifest() -> dict:
    path = resolve_path("data", "processed", "download_manifest.json")
    if not path.exists():
        return {"success": True, "data": {}}
    with open(path, "r", encoding="utf-8") as f:
        return {"success": True, "data": json.load(f)}


# --- Start Download ---
@app.post("/api/download/start")
def start_download(req: DownloadStartRequest) -> dict:
    """Trigger download script asynchronously."""
    cmd = [
        sys.executable,
        str(resolve_path("scripts", "01_download_csi2000_data.py")),
        "--start-date", req.startDate,
        "--end-date", req.endDate,
        "--index-code", req.indexCode,
        "--adjust", req.adjust,
        "--sleep", str(req.sleep),
    ]
    if req.force:
        cmd.append("--force")
    if req.skipFundamental:
        cmd.append("--skip-fundamental")
    if req.limit > 0:
        cmd.extend(["--limit", str(req.limit)])

    # Run in background (simplified; real use would use Celery/background tasks)
    subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
    return {"success": True, "message": "下载任务已启动", "taskId": "download-1"}


# --- Process: Finalize ---
@app.post("/api/process/finalize")
def process_finalize() -> dict:
    cmd = [
        sys.executable,
        str(resolve_path("scripts", "02_finalize_partial.py")),
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr if result.stderr else None,
    }


# --- Process: Synthesize Index ---
@app.post("/api/process/synthesize-index")
def process_synthesize_index() -> dict:
    cmd = [
        sys.executable,
        str(resolve_path("scripts", "03_synthesize_index_proxy.py")),
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr if result.stderr else None,
    }


# --- Process: Synthesize Spot ---
@app.post("/api/process/synthesize-spot")
def process_synthesize_spot() -> dict:
    cmd = [
        sys.executable,
        str(resolve_path("scripts", "04_synthesize_spot_snapshot.py")),
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr if result.stderr else None,
    }


# ---------------------------------------------------------------------------
# Static Files (production build)
# ---------------------------------------------------------------------------
dist_dir = Path(__file__).resolve().parent.parent / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
