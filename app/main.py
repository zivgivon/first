from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models import Base, Person, PersonFeature
from app.schemas import SearchRequest, SearchResponse, PersonOut
from app.features import recompute_all_features, get_or_compute_features, vector_to_summary
from app.similarity import find_similar_groups
import numpy as np

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Group Similarity Search")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/persons", response_model=list[PersonOut])
def list_persons(db: Session = Depends(get_db)):
    return db.query(Person).order_by(Person.id).all()


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest, db: Session = Depends(get_db)):
    if not req.person_ids:
        raise HTTPException(status_code=400, detail="person_ids must not be empty")

    existing = {p.id for p in db.query(Person).filter(Person.id.in_(req.person_ids)).all()}
    missing = set(req.person_ids) - existing
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown person IDs: {sorted(missing)}")

    query_vecs = [get_or_compute_features(db, pid) for pid in req.person_ids]
    query_mean = np.mean(query_vecs, axis=0).tolist()
    query_summary = vector_to_summary(query_mean)

    results = find_similar_groups(db, req.person_ids)

    return SearchResponse(
        query_group=req.person_ids,
        query_profile_summary=query_summary,
        results=results,
    )


@app.post("/api/recompute-features")
def recompute(db: Session = Depends(get_db)):
    all_ids = [p.id for p in db.query(Person).all()]
    recompute_all_features(db, all_ids)
    return {"status": "ok", "persons_updated": len(all_ids)}
