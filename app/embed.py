import hashlib
import math
import re

DIM = 128


class HashingEmbedder:
    """Bag-of-words hashing embedder.

    Good enough for keyword retrieval in this demo and in tests. A production
    version would swap this for an embedding model without changing callers.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * DIM
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            if len(token) < 3:
                continue
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % DIM
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
