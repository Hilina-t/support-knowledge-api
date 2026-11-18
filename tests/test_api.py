from fastapi.testclient import TestClient

from app.llm import FakeLLM
from app.main import create_app
from app.settings import Settings
from app.store import KnowledgeStore


def make_client(tmp_path):
    store = KnowledgeStore(tmp_path)
    application = create_app(Settings(data_dir=tmp_path), store=store, llm=FakeLLM())
    return TestClient(application)


def test_health(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/health").json() == {"status": "ok"}


def test_seed_articles_are_searchable(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/ask", json={"question": "How do I reset a forgotten password?"})
    body = response.json()
    assert response.status_code == 200
    assert body["sources"][0]["title"] == "Reset a forgotten password"
    assert body["answer"].startswith('From "Reset a forgotten password"')


def test_added_article_is_retrieved_ahead_of_unrelated_ones(tmp_path):
    client = make_client(tmp_path)
    created = client.post(
        "/documents",
        json={
            "title": "Replace a failed fan",
            "body": "A fan failure raises a chassis alarm. Swap the fan within two minutes so the node does not overheat.",
        },
    )
    assert created.status_code == 201
    response = client.post("/ask", json={"question": "What should I do when a fan fails?"})
    assert response.json()["sources"][0]["title"] == "Replace a failed fan"


def test_blank_question_is_rejected(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/ask", json={"question": ""}).status_code == 422
