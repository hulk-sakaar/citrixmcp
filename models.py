from pydantic import BaseModel


class SearchHit(BaseModel):
    title: str
    url: str
    product: str | None = None
    snippet: str | None = None


class CleanDoc(BaseModel):
    title: str
    url: str
    markdown: str
    last_updated: str | None = None
    contributed_by: str | None = None


class ApiEndpoint(BaseModel):
    title: str
    url: str
    method: str | None = None
    path: str | None = None
    markdown: str


class ProductInfo(BaseModel):
    product: str
    url_prefix: str
    page_count: int = 0
