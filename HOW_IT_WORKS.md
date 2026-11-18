# How the Support Knowledge API works

This is a small customer-support API. You give it articles, then you ask a question in plain language. It finds the article that matches and answers from that article, instead of letting a model invent an answer from memory.

## What happens when you ask a question

Say the question is "How do I reset a forgotten password?"

1. FastAPI receives `POST /ask` and checks that the question is not empty. An empty question is rejected with status 422 before any search runs.
2. The question is turned into a list of 128 numbers, called an embedding. The same function was used earlier to turn each article into 128 numbers.
3. Chroma compares the question's numbers with every article's numbers and returns the closest three. For this question, "Reset a forgotten password" comes back first.
4. Those three articles are the only text the model is allowed to see. The whole knowledge base is not pasted into the prompt.
5. The model writes an answer from the top article. The response also includes the sources, so a caller can see which article was used.

With no API key, the local stand-in model returns the top article directly:

```text
From "Reset a forgotten password": Open the sign-in page and choose Forgot password...
```

With `LLM_PROVIDER=openai`, the same retrieved articles are sent to OpenAI, and the model writes the answer in its own words. The instruction in the prompt says to use only those articles and to say it does not know if they do not contain the answer.

## Why there are two databases

An article is saved twice, on purpose.

SQLite (`data/knowledge.db`) stores the real record: id, title, full body, and the time it was created. `GET /documents` reads from here. The table is:

```sql
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

Chroma (`data/chroma`) stores the same id plus the 128 numbers. It is only used for "which articles are closest to this question?" SQLite is a poor fit for that comparison, and Chroma is a poor fit for listing articles in created order. The id is the same in both, so a search hit can be tied back to the article.

`POST /documents` writes SQLite first, then Chroma. The first time the database is empty, the app loads three sample articles: password reset, failover, and invoices.

## How the numbers are made

`HashingEmbedder` does not call a model. It lowercases the text, keeps words of at least three letters, and drops each word into one of 128 buckets using an MD5 hash. A word that appears twice adds 2 to that bucket. The list is then scaled so its length is 1, which lets Chroma compare direction rather than raw word count.

Articles that share words land closer together. "reset" and "password" pull the password article toward a password question. "fan" and "failure" pull a fan article toward a fan question.

This is keyword overlap, not real meaning. "The node went down" and "a failover happened" do not match unless they share words. A production version replaces this class with a model embedding such as OpenAI's `text-embedding-3-small`. `KnowledgeStore` already takes the embedder as a constructor argument, so the search code stays the same.

## The two models

Both classes have one method, `complete(question, sources)`.

`FakeLLM` does not call the network. If retrieval returned nothing, it says it has no article. Otherwise it quotes the title and body of the top hit. Tests and a local demo use this.

`OpenAILLM` builds a prompt from the retrieved titles and excerpts, sends it to `https://api.openai.com/v1/chat/completions`, and returns the text. Temperature is 0 so the same prompt tends to give the same answer. It is selected only when `LLM_PROVIDER=openai` and `OPENAI_API_KEY` is set. If the provider is openai and the key is missing, startup fails immediately instead of failing on the first question.

## The HTTP surface

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Returns `{"status": "ok"}` |
| POST | `/documents` | Saves an article. Body is `{"title", "body"}`. Returns the saved article with an id. |
| GET | `/documents` | Lists articles from SQLite, oldest first. |
| POST | `/ask` | Body is `{"question"}`. Returns `{"answer", "sources"}`. |

Pydantic models in `app/schemas.py` set the limits: a title up to 200 characters, a body up to 20,000, a question up to 2,000. FastAPI uses those models to reject bad JSON before the handler runs. The interactive page is http://127.0.0.1:8000/docs while the server is running.

`create_app()` builds the FastAPI app and lets tests pass in their own store and model. The module-level `app = create_app()` is what `uvicorn app.main:app` serves.

## Tests

`pytest` runs four tests, all against a temporary directory, so they do not touch the local `data/` folder.

- `/health` returns ok.
- The seeded password article is the first source for a password question, and the answer cites that title.
- A newly added fan article outranks the seeded articles for a fan question.
- An empty question is rejected with 422.

## What is deliberately small

Each article is one vector. A long runbook would be split into chunks, and each chunk would be embedded separately. The search returns a 400-character excerpt, not a ranked score to the caller. There is no login, no rate limit, and no check that the answer actually agrees with the article. The Docker file runs the same app on port 8000. That image is what would go on Kubernetes later.

The short version: the question is embedded, only the nearest articles go into the prompt, and the model is a replaceable part so the tests never call the network.
