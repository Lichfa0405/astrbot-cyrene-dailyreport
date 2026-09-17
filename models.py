# models.py
from pydantic import BaseModel


class Hitokoto(BaseModel):
    id: int
    uuid: str
    hitokoto: str
    type: str
    from_who: str | None
    creator: str
    creator_uid: int
    reviewer: int
    commit_from: str
    created_at: str
    length: int


class SixDataTo(BaseModel):
    news: list[str]
    tip: str
    updated: int
    url: str
    cover: str


class SixData(BaseModel):
    status: int
    message: str
    data: SixDataTo