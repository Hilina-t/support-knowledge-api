import json
import urllib.request


class FakeLLM:
    """Returns an answer grounded in the retrieved titles, with no network call."""

    def complete(self, question: str, sources: list[dict]) -> str:
        if not sources:
            return "I don't have an article that answers that."
        top = sources[0]
        excerpt = top["excerpt"].split("\n", 1)[-1]
        return f'From "{top["title"]}": {excerpt}'


class OpenAILLM:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, question: str, sources: list[dict]) -> str:
        context = "\n\n".join(
            f"Title: {source['title']}\n{source['excerpt']}" for source in sources
        )
        prompt = (
            "Answer the question using only the articles below. "
            "If they do not contain the answer, say you don't know. "
            "Mention the article title you used.\n\n"
            f"Articles:\n{context}\n\nQuestion: {question}"
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode())
        return body["choices"][0]["message"]["content"].strip()
