import os
import re
import json

NAME_TABLE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "name_transliteration.json"
)

# Course / module codes: CS101, МАТ-301, CS-202, EENG4010, Мат301
_COURSE_CODE_RE = re.compile(r"\b[A-Za-zА-ЯЁа-яё]{2,5}-?\d{2,5}\b")
# Standalone uppercase abbreviations (Latin or Cyrillic), 2-6 letters
_ABBR_RE = re.compile(r"\b[A-ZА-ЯЁ]{2,6}\b")

_NAME_TABLE = None


class Token:
    """A protected span in the source text.

    kind:
      - 'code': course / module code, must survive translation unchanged
      - 'abbr': standalone abbreviation (MIT, МГУ), keep original
      - 'name': person name with a canonical transliteration
    """

    __slots__ = ("text", "kind")

    def __init__(self, text, kind):
        self.text = text
        self.kind = kind


def _load_names():
    global _NAME_TABLE
    if _NAME_TABLE is not None:
        return _NAME_TABLE
    _NAME_TABLE = {}
    if os.path.isfile(NAME_TABLE_PATH):
        try:
            with open(NAME_TABLE_PATH, "r", encoding="utf-8") as f:
                obj = json.load(f)
            for pair in obj.get("pairs", []):
                source = pair.get("source")
                target = pair.get("target")
                for src_name, tgt_name in pair.get("names", {}).items():
                    _NAME_TABLE[(source, target, src_name)] = tgt_name
        except Exception as e:
            print("name table load error:", str(e))
    return _NAME_TABLE


def detect(source_text, source, target):
    """Find protected tokens in the source text."""
    tokens = []
    codes = set()
    for m in _COURSE_CODE_RE.finditer(source_text):
        codes.add(m.group(0))
        tokens.append(Token(m.group(0), "code"))
    for m in _ABBR_RE.finditer(source_text):
        tok = m.group(0)
        # skip abbreviations that are part of an already-captured code
        if any(c.startswith(tok) for c in codes):
            continue
        tokens.append(Token(tok, "abbr"))
    names = _load_names()
    for (s, t, src_name), tgt_name in names.items():
        if s == source and t == target and src_name and src_name in source_text:
            tokens.append(Token(src_name, "name"))
    return tokens


def _mt(translator, text):
    """How argos translates a single token (used to locate it in output)."""
    try:
        hyp = translator.hypotheses(text, 1)
        return hyp[0].value if hyp else text
    except Exception:
        return text


def postcorrect(translator, translated_text, source_text, tokens, source, target):
    """Restore protected tokens in the machine-translated output.

    - 'code' / 'abbr': language-invariant -> force the original form back
    - 'name': replace argos' transliteration with the canonical one
    """
    if not tokens:
        return translated_text
    names = _load_names()
    for tok in tokens:
        if tok.kind == "name":
            canonical = names.get((source, target, tok.text))
            if not canonical:
                continue
            mt = _mt(translator, tok.text)
            if mt and mt != canonical and mt in translated_text:
                translated_text = translated_text.replace(mt, canonical)
        else:
            # invariant token: argos may transliterate / cyrillize it; restore
            mt = _mt(translator, tok.text)
            if mt and mt != tok.text and mt in translated_text:
                translated_text = translated_text.replace(mt, tok.text)
    return translated_text
