import os
import re
import json
import sqlite3
from expiringdict import ExpiringDict

DEFAULT_DB_PATH = "db/glossary.db"
DEFAULT_SEED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "glossary_zh_ru.json"
)


class Database:
    """SQLite-backed bilingual terminology glossary.

    Stores (source_lang, target_lang, src_term, tgt_term) rows. When the
    translation pipeline produces output, :meth:`apply` rewrites the
    machine-translated rendering of any glossary source term with the
    canonical target term, so campus-approved terminology wins.
    """

    def __init__(self, db_path=DEFAULT_DB_PATH, seed_path=DEFAULT_SEED_PATH,
                 max_cache_len=1000, max_cache_age=600):
        self.db_path = db_path
        self.seed_path = seed_path
        self._term_cache = ExpiringDict(max_len=max_cache_len, max_age_seconds=max_cache_age)
        # cache of "how did argos translate this single source term"
        self._mt_cache = ExpiringDict(max_len=2000, max_age_seconds=3600)
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.c = sqlite3.connect(db_path, check_same_thread=False)
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS glossary (
            "source"	TEXT NOT NULL,
            "target"	TEXT NOT NULL,
            "src_term"	TEXT NOT NULL,
            "tgt_term"	TEXT NOT NULL,
            PRIMARY KEY (source, target, src_term)
        );"""
        )
        self.c.commit()
        self._seed()

    def _seed(self):
        if not self.seed_path or not os.path.isfile(self.seed_path):
            return
        try:
            with open(self.seed_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for pair in data.get("pairs", []):
                source = pair.get("source")
                target = pair.get("target")
                for src_term, tgt_term in pair.get("terms", {}).items():
                    if source and target and src_term and tgt_term:
                        self.c.execute(
                            "INSERT OR IGNORE INTO glossary (source, target, src_term, tgt_term) VALUES (?, ?, ?, ?)",
                            (source, target, src_term, tgt_term),
                        )
            self.c.commit()
        except Exception as e:
            print("glossary seed error:", str(e))

    def _invalidate(self, source, target):
        try:
            del self._term_cache[(source, target)]
        except KeyError:
            pass

    def get_terms(self, source, target):
        key = (source, target)
        cached = self._term_cache.get(key)
        if cached is not None:
            return cached
        rows = self.c.execute(
            "SELECT src_term, tgt_term FROM glossary WHERE source = ? AND target = ?",
            (source, target),
        ).fetchall()
        terms = [(r[0], r[1]) for r in rows]
        self._term_cache[key] = terms
        return terms

    def add_term(self, source, target, src_term, tgt_term):
        self.c.execute(
            "INSERT OR REPLACE INTO glossary (source, target, src_term, tgt_term) VALUES (?, ?, ?, ?)",
            (source, target, src_term, tgt_term),
        )
        self.c.commit()
        self._invalidate(source, target)
        return True

    def remove_term(self, source, target, src_term):
        self.c.execute(
            "DELETE FROM glossary WHERE source = ? AND target = ? AND src_term = ?",
            (source, target, src_term),
        )
        self.c.commit()
        self._invalidate(source, target)
        return True

    def list_terms(self, source=None, target=None):
        if source and target:
            rows = self.c.execute(
                "SELECT source, target, src_term, tgt_term FROM glossary WHERE source = ? AND target = ?",
                (source, target),
            ).fetchall()
        else:
            rows = self.c.execute(
                "SELECT source, target, src_term, tgt_term FROM glossary"
            ).fetchall()
        return [{"source": r[0], "target": r[1], "src_term": r[2], "tgt_term": r[3]} for r in rows]

    def _mt_term(self, translator, src_term):
        """How does argos translate a single source term? (cached)."""
        cached = self._mt_cache.get(src_term)
        if cached is not None:
            return cached
        try:
            hyp = translator.hypotheses(src_term, 1)
            mt = hyp[0].value if hyp else src_term
        except Exception:
            mt = src_term
        self._mt_cache[src_term] = mt
        return mt

    @staticmethod
    def _replacer(needle):
        # Word-boundary aware substitution so we don't mangle substrings.
        return re.compile(r"(?<![A-Za-zА-Яа-яЁё0-9])" + re.escape(needle) + r"(?![A-Za-zА-Яа-яЁё0-9])")

    def apply(self, translator, source_text, translated_text, alternatives, source, target):
        """Rewrite machine output so glossary target terms are preferred."""
        terms = self.get_terms(source, target)
        if not terms:
            return translated_text, alternatives
        alternatives = alternatives or []
        for src_term, tgt_term in terms:
            if not src_term or src_term not in source_text:
                continue
            mt_term = self._mt_term(translator, src_term)
            if not mt_term or mt_term == tgt_term or mt_term not in translated_text:
                continue
            pattern = self._replacer(mt_term)
            translated_text = pattern.sub(tgt_term, translated_text)
            alternatives = [pattern.sub(tgt_term, a) if mt_term in a else a for a in alternatives]
        return translated_text, alternatives
