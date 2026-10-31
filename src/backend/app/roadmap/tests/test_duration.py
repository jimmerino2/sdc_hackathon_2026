from types import SimpleNamespace

from app.roadmap import duration


def src(kind="video", minutes=None, title="T"):
    return SimpleNamespace(source_type=kind, title=title, duration_minutes=minutes)


def test_a_stated_length_wins_and_names_the_resource():
    assert duration.estimate("tech", None, [src("project", 25), src("video", 95, "Full course")]) == (95, "stated", "Full course")


def test_a_short_clip_does_not_count_as_the_time_to_learn_a_skill():
    minutes, basis, via = duration.estimate("tech", None, [src("video", 12)])
    assert basis == "estimated" and via is None and minutes == duration.formula_minutes("video", None)


def test_the_formula_is_base_times_depth_rounded_to_a_quarter_hour():
    assert duration.formula_minutes("project", None) == 360          # tools have no level
    assert duration.formula_minutes("video", 0) == 60                # 120 x 0.5
    assert duration.formula_minutes("video", 7) == 180               # 120 x 1.5
    assert duration.formula_minutes("certificate", 3.5) == 600       # 600 x 1.0
    assert duration.formula_minutes("activity", 4) % 15 == 0


def test_a_deeper_skill_never_takes_less():
    times = [duration.formula_minutes("certificate", lvl) for lvl in range(8)]
    assert times == sorted(times)


def test_with_no_resource_the_usual_kind_for_the_skill_is_used():
    assert duration.estimate("tech", None, [])[0] == duration.BASE_MINUTES["project"]
    assert duration.estimate("knowledge", 4, [])[1] == "estimated"
