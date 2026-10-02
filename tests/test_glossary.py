import os

from libretranslate.glossary import Database


class _Hyp:
    def __init__(self, value):
        self.value = value


class FakeTranslator:
    """Mimics argostranslate's translator.hypotheses(text, n)."""

    _MAP = {
        "数据结构": "структуры данные",
        "线性代数": "линейная алгебра",
        "Структуры данных": "数据结构",
    }

    def hypotheses(self, text, n):
        return [_Hyp(self._MAP.get(text, text))]


def _db():
    return Database(":memory:", seed_path="")


def test_add_and_get():
    db = _db()
    db.add_term("zh", "ru", "数据结构", "Структуры данных")
    assert ("数据结构", "Структуры данных") in db.get_terms("zh", "ru")


def test_remove():
    db = _db()
    db.add_term("zh", "ru", "数据结构", "Структуры данных")
    db.remove_term("zh", "ru", "数据结构")
    assert db.get_terms("zh", "ru") == []


def test_apply_rewrites_machine_output():
    db = _db()
    db.add_term("zh", "ru", "数据结构", "Структуры данных")
    tr = FakeTranslator()
    # argos mistranslates the term; apply() must restore the canonical form
    out, alts = db.apply(tr, "数据结构导论", "структуры данные введение", [], "zh", "ru")
    assert out == "Структуры данных введение"


def test_apply_skips_when_source_term_absent():
    db = _db()
    db.add_term("zh", "ru", "数据结构", "Структуры данных")
    tr = FakeTranslator()
    out, _ = db.apply(tr, "操作系统", "операционные системы", [], "zh", "ru")
    assert out == "операционные системы"


def test_apply_corrects_alternatives():
    db = _db()
    db.add_term("zh", "ru", "数据结构", "Структуры данных")
    tr = FakeTranslator()
    _, alts = db.apply(tr, "数据结构", "структуры данные", ["структуры данные курс"], "zh", "ru")
    assert alts == ["Структуры данных курс"]


def test_seed_loads_terms(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(
        '{"pairs":[{"source":"zh","target":"ru","terms":{"算法":"Алгоритмы"}}]}',
        encoding="utf-8",
    )
    db = Database(str(tmp_path / "g.db"), seed_path=str(seed))
    assert ("算法", "Алгоритмы") in db.get_terms("zh", "ru")
