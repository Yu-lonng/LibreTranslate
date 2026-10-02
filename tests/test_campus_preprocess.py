from libretranslate.campus_preprocess import detect, postcorrect


class _Hyp:
    def __init__(self, value):
        self.value = value


class FakeTranslator:
    """Mimics argostranslate's translator.hypotheses(text, n)."""

    _MAP = {
        "CS101": "КС101",          # argos cyrillicizes the code
        "MIT": "мит",             # argos lowercases / transliterates abbr
        "МГУ": "Мгу",
        "王强": "Ван Цянь",         # argos uses wrong tone/ending
        "李娜": "Ли На",
        "Иванов": "伊万诺夫",
    }

    def hypotheses(self, text, n):
        return [_Hyp(self._MAP.get(text, text))]


def test_detect_course_code():
    toks = detect("课程 CS101 明天考试", "zh", "ru")
    assert any(t.text == "CS101" and t.kind == "code" for t in toks)


def test_detect_abbreviation():
    toks = detect("讲座由 MIT 与 МГУ 联合举办", "zh", "ru")
    kinds = {(t.text, t.kind) for t in toks}
    assert ("MIT", "abbr") in kinds
    assert ("МГУ", "abbr") in kinds


def test_detect_cyrillic_code():
    toks = detect("Экзамен по МАТ-301", "ru", "zh")
    assert any(t.text == "МАТ-301" and t.kind == "code" for t in toks)


def test_postcorrect_restores_code():
    tr = FakeTranslator()
    toks = detect("课程 CS101 明天考试", "zh", "ru")
    out = postcorrect(tr, "КС101 экзамен", "课程 CS101 明天考试", toks, "zh", "ru")
    assert "CS101" in out
    assert "КС101" not in out


def test_postcorrect_restores_abbreviation():
    tr = FakeTranslator()
    toks = detect("讲座由 MIT 联合举办", "zh", "ru")
    out = postcorrect(tr, "лекция организована мит", "讲座由 MIT 联合举办", toks, "zh", "ru")
    assert "MIT" in out


def test_postcorrect_canonicalizes_name():
    tr = FakeTranslator()
    toks = detect("请王强同学发言", "zh", "ru")
    out = postcorrect(tr, "Просим Ван Цянь выступить", "请王强同学发言", toks, "zh", "ru")
    assert "Ван Цян" in out
    assert "Ван Цянь" not in out


def test_postcorrect_no_tokens():
    tr = FakeTranslator()
    out = postcorrect(tr, "привет", "你好", [], "zh", "ru")
    assert out == "привет"
