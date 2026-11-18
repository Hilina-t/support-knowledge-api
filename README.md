# Support Knowledge API

A small retrieval-augmented API for customer-support articles.

`POST /documents` stores an article in SQLite and a vector in Chroma. `POST /ask` retrieves the closest articles and asks an LLM to answer from those articles only. With no API key it uses a local fake model, so the retrieval path still runs.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question": "How do I reset a forgotten password?"}'
```

Three sample articles are loaded the first time the database is empty.

## Use a real model

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```

## What to say about it

The API keeps article text in SQLite and embeddings in Chroma. Ask does not send the whole knowledge base to the model. It embeds the question, retrieves the nearest articles, and puts only those in the prompt, along with their titles so the answer can cite a source. The embedder and the LLM are separate objects, which is why the tests run with no network and no API key. In production the hashing embedder would be replaced with a model embedding, and the service would add authentication, rate limits, and an evaluation set of questions with known articles.
