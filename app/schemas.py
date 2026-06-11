from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SearchRequest(BaseModel):
    person_ids: List[int]


class GroupResult(BaseModel):
    rank: int
    similarity: float
    members: List[int]
    size: int
    profile_summary: Dict[str, Any]


class SearchResponse(BaseModel):
    query_group: List[int]
    query_profile_summary: Dict[str, Any]
    results: List[GroupResult]


class PersonOut(BaseModel):
    id: int
    name: str
    age: int
    region: str

    class Config:
        from_attributes = True
