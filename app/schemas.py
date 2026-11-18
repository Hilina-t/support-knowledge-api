from pydantic import BaseModel, Field


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)


class DocumentOut(BaseModel):
    id: str
    title: str
    body: str
    created_at: str


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    id: str
    title: str
    excerpt: str


class AskOut(BaseModel):
    answer: str
    sources: list[Source]
