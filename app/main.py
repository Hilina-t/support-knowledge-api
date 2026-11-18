from fastapi import FastAPI

from app.llm import FakeLLM, OpenAILLM
from app.schemas import AskIn, AskOut, DocumentIn, DocumentOut
from app.settings import Settings
from app.store import KnowledgeStore

SEED_ARTICLES = [
    (
        "Reset a forgotten password",
        "Open the sign-in page and choose Forgot password. Enter the account email. "
        "The reset link expires after 30 minutes. If no email arrives, check spam, then "
        "ask an administrator to confirm the address on the account.",
    ),
    (
        "Read a high-availability failover",
        "A failover moves the active node to its partner when the active node is unreachable. "
        "Customer traffic stays on the same service address. After giveback, confirm both "
        "nodes are healthy before closing the incident.",
    ),
    (
        "Export an invoice",
        "Billing invoices are available under Account, then Billing, then Invoices. "
        "Choose the month and download the PDF. Invoices are generated on the first day of the next month.",
    ),
]


def build_llm(settings: Settings):
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLM(settings.openai_api_key, settings.openai_model)
    return FakeLLM()


def create_app(settings: Settings | None = None, store: KnowledgeStore | None = None, llm=None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Support Knowledge API", version="0.1.0")
    app.state.store = store or KnowledgeStore(settings.data_dir)
    app.state.llm = llm or build_llm(settings)
    if not app.state.store.list_documents():
        for title, body in SEED_ARTICLES:
            app.state.store.add(title, body)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/documents", response_model=DocumentOut, status_code=201)
    def create_document(payload: DocumentIn) -> dict:
        return app.state.store.add(payload.title, payload.body)

    @app.get("/documents", response_model=list[DocumentOut])
    def list_documents() -> list[dict]:
        return app.state.store.list_documents()

    @app.post("/ask", response_model=AskOut)
    def ask(payload: AskIn) -> dict:
        sources = app.state.store.search(payload.question)
        answer = app.state.llm.complete(payload.question, sources)
        return {"answer": answer, "sources": sources}

    return app


app = create_app()
