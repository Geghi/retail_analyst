import re

from .trio import Trio, load_trios

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "compare",
        "compared",
        "did",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "or",
        "show",
        "than",
        "that",
        "the",
        "their",
        "there",
        "to",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    ]
)


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


def find_similar(question: str, trios: list[Trio] | None = None, limit: int = 3) -> list[Trio]:
    wanted = tokens(question)
    candidates = load_trios() if trios is None else trios
    scored = [(len(wanted & tokens(trio.question)), trio) for trio in candidates]
    ranked = sorted((item for item in scored if item[0]), key=lambda item: (-item[0], item[1].id))
    return [trio for _, trio in ranked[:limit]]
