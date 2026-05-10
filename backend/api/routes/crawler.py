from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["crawler"])

class CrawlRequest(BaseModel):
    url: str

@router.post("/crawl")
async def crawl(req: CrawlRequest, token: str = Header(..., alias="token")):
    if "free_user" in token:
        raise HTTPException(status_code=403, detail="Contributor only")
    return {"ok": True}

@router.get("/crawl/status")
async def crawl_status():
    return {"queue_size": 0, "pages_crawled": 0}
