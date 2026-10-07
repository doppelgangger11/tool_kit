from __future__ import annotations

_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU = "йцукенгшщзхъфывапролджэячсмитьбю.ё"

_EN_TO_RU = dict(zip(_EN, _RU))
_RU_TO_EN = dict(zip(_RU, _EN))


def switch_layout(text: str) -> str:
    """'ср' -> 'ch', 'ch' -> 'ср'. Символы вне раскладки остаются как есть."""
    out = []
    for ch in text.lower():
        out.append(_RU_TO_EN.get(ch) or _EN_TO_RU.get(ch) or ch)
    return "".join(out)


def _score_token(token: str, text: str, fuzzy: bool) -> int | None:
    if not token:
        return 0

    if text == token:
        return 1000

    if text.startswith(token):
        return 900 - min(len(text) - len(token), 99)

    # совпадение с началом любого слова
    words = text.replace("-", " ").replace("_", " ").replace(".", " ").split()
    for word in words:
        if word.startswith(token):
            return 800 - min(len(text) - len(token), 99)

    index = text.find(token)
    if index >= 0:
        return 600 - min(index, 99)

    # подпоследовательность: "vsc" -> "Visual Studio Code".
    # Только для коротких названий: в длинном тексте она совпадает почти с чем угодно.
    if fuzzy and len(token) >= 2 and len(text) <= 80:
        pos = -1
        first = None
        for ch in token:
            pos = text.find(ch, pos + 1)
            if pos < 0:
                return None
            if first is None:
                first = pos
        spread = pos - first + 1 - len(token)   # сколько лишних символов между
        return max(300 - spread * 5, 1)

    return None


def score(query: str, text: str, fuzzy: bool = True) -> int | None:
    """Оценка совпадения запроса с текстом. None - не подходит."""
    text = text.lower()
    tokens = query.lower().split()

    if not tokens:
        return 0

    total = 0
    for token in tokens:
        value = _score_token(token, text, fuzzy)
        if value is None:
            return None
        total += value

    return total // len(tokens)


def best_score(query: str, text: str, fuzzy: bool = True) -> int | None:
    """Лучшая оценка среди запроса и его версии в другой раскладке."""
    candidates = [score(query, text, fuzzy), score(switch_layout(query), text, fuzzy)]
    candidates = [c for c in candidates if c is not None]
    return max(candidates) if candidates else None
