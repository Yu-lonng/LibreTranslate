from libretranslate.scenarios import list_scenarios, get_scenario, render_scenario


def test_list_non_empty():
    items = list_scenarios()
    assert len(items) >= 1
    ids = [i["id"] for i in items]
    assert "courseware_title" in ids


def test_get_scenario():
    s = get_scenario("courseware_title")
    assert s is not None
    assert "course" in s["variables"]


def test_get_unknown_returns_none():
    assert get_scenario("does_not_exist") is None


def test_render_both_sides():
    r = render_scenario("courseware_title", {
        "course": "数据结构",
        "chapter": "3",
        "lecturer": "王强",
    })
    assert r is not None
    assert "数据结构" in r["zh"]
    assert "Лекция 3" in r["ru"]
    assert "王强" in r["zh"]


def test_render_missing_variable_left_as_placeholder():
    r = render_scenario("courseware_title", {"course": "算法"})
    # chapter and lecturer were not provided -> kept as ${chapter} / ${lecturer}
    assert "${chapter}" in r["zh"]


def test_render_email_template():
    r = render_scenario("email_to_instructor", {
        "instructor_name": "Иванов",
        "student_name": "李娜",
        "course_name": "高等数学",
        "topic": "极限",
        "date": "周五",
    })
    assert "Иванов" in r["ru"]
    assert "李娜" in r["zh"]
