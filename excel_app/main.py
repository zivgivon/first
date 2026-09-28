"""
Group Similarity Search — Excel edition
Run:  python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
import io
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from features import compute_all_features, group_profile, vector_to_summary, FEATURE_NAMES
from similarity import find_similar_groups

app = FastAPI(title="Group Similarity Search")

_state: dict = {"loaded": False, "persons": None, "feature_df": None}

REQUIRED_PERSONS_COLS = {"id", "name"}
REQUIRED_CEL_COLS = {"person_id", "timestamp", "call_duration_sec", "sms_count", "contact_id", "call_type"}
REQUIRED_LOC_COLS = {"person_id", "timestamp", "lat", "lon"}
REQUIRED_CYB_COLS = {"person_id", "timestamp", "domain", "data_volume_kb", "protocol"}


def _validate(df: pd.DataFrame, name: str, required_cols: set):
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"{name}.xlsx is missing columns: {missing}")


def _empty_df(cols):
    return pd.DataFrame(columns=list(cols))


def _load_from_dfs(df_persons, df_cel=None, df_loc=None, df_cyb=None):
    if df_persons is None or len(df_persons) == 0:
        raise ValueError("persons.xlsx is required and must not be empty")
    _validate(df_persons, "persons", REQUIRED_PERSONS_COLS)
    if df_cel is not None:
        _validate(df_cel, "cellular", REQUIRED_CEL_COLS)
    else:
        df_cel = _empty_df(REQUIRED_CEL_COLS)
    if df_loc is not None:
        _validate(df_loc, "location", REQUIRED_LOC_COLS)
    else:
        df_loc = _empty_df(REQUIRED_LOC_COLS)
    if df_cyb is not None:
        _validate(df_cyb, "cyber", REQUIRED_CYB_COLS)
    else:
        df_cyb = _empty_df(REQUIRED_CYB_COLS)

    for df, ts_col in [(df_cel, "timestamp"), (df_loc, "timestamp"), (df_cyb, "timestamp")]:
        if ts_col in df.columns and len(df):
            df[ts_col] = pd.to_datetime(df[ts_col])

    feature_df = compute_all_features(df_persons, df_cel, df_loc, df_cyb)
    _state["persons"] = df_persons
    _state["feature_df"] = feature_df
    _state["loaded"] = True
    return len(df_persons)


TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = TEMPLATES_DIR / "index.html"
    with open(html_path, encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/status")
async def status():
    if not _state["loaded"]:
        return {"loaded": False, "persons": 0}
    return {"loaded": True, "persons": len(_state["persons"])}


@app.get("/api/persons")
async def get_persons():
    if not _state["loaded"]:
        raise HTTPException(400, "No data loaded. Upload files first.")
    df = _state["persons"]
    return df[["id", "name"]].to_dict(orient="records")


class SearchRequest(BaseModel):
    person_ids: list[int]


@app.post("/api/search")
async def search(req: SearchRequest):
    if not _state["loaded"]:
        raise HTTPException(400, "No data loaded. Upload files first.")
    feature_df = _state["feature_df"]
    valid_ids = [pid for pid in req.person_ids if pid in feature_df.index]
    if not valid_ids:
        raise HTTPException(400, "None of the provided IDs have feature data.")
    query_vec = group_profile(feature_df, valid_ids)
    query_summary = vector_to_summary(query_vec)
    results = find_similar_groups(feature_df, valid_ids)
    persons_df = _state["persons"].set_index("id")
    enriched = []
    for r in results:
        names = []
        for mid in r["members"]:
            if mid in persons_df.index:
                names.append(persons_df.loc[mid, "name"])
        enriched.append({**r, "member_names": names[:5]})
    return {"query_profile": query_summary, "results": enriched, "feature_names": FEATURE_NAMES}


@app.post("/api/upload")
async def upload(
    persons: UploadFile = File(...),
    cellular: Optional[UploadFile] = File(None),
    location: Optional[UploadFile] = File(None),
    cyber: Optional[UploadFile] = File(None),
):
    async def read_excel(f: Optional[UploadFile]):
        if f is None:
            return None
        content = await f.read()
        return pd.read_excel(io.BytesIO(content))

    try:
        df_persons = await read_excel(persons)
        df_cel = await read_excel(cellular)
        df_loc = await read_excel(location)
        df_cyb = await read_excel(cyber)
        n = _load_from_dfs(df_persons, df_cel, df_loc, df_cyb)
        return {"ok": True, "persons": n}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/reload")
async def reload_from_disk():
    data_dir = Path(__file__).parent / "data"
    try:
        df_persons = pd.read_excel(data_dir / "persons.xlsx")
        df_cel = pd.read_excel(data_dir / "cellular.xlsx") if (data_dir / "cellular.xlsx").exists() else None
        df_loc = pd.read_excel(data_dir / "location.xlsx") if (data_dir / "location.xlsx").exists() else None
        df_cyb = pd.read_excel(data_dir / "cyber.xlsx") if (data_dir / "cyber.xlsx").exists() else None
        n = _load_from_dfs(df_persons, df_cel, df_loc, df_cyb)
        return {"ok": True, "persons": n}
    except FileNotFoundError:
        raise HTTPException(400, "data/persons.xlsx not found. Place Excel files in the data/ folder.")
    except Exception as e:
        raise HTTPException(400, str(e))
