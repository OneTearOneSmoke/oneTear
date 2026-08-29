import pytest

from aitest.core.case import Case
from aitest.core.suite import Suite


def test_suite_load_dir_with_single_doc(tmp_path):
    (tmp_path / "a.yaml").write_text("id: a\ntags: [t1]\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("id: b\ntags: [t2]\n", encoding="utf-8")
    s = Suite.load_dir(str(tmp_path), pattern="*.yaml")
    assert {c.id for c in s.cases} == {"a", "b"}


def test_suite_load_dir_multi_doc_raises(tmp_path):
    (tmp_path / "m.yaml").write_text("id: a\n---\nid: b\n", encoding="utf-8")
    with pytest.raises(Exception):
        Suite.load_dir(str(tmp_path))


def test_suite_filter_and_search(tmp_path):
    (tmp_path / "a.yaml").write_text("id: ai.sort\ntags: [sort]\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("id: ai.llm\ntags: [llm]\n", encoding="utf-8")
    s = Suite.load_dir(str(tmp_path))
    only_sort = s.filter(tags=["sort"])
    assert {c.id for c in only_sort.cases} == {"ai.sort"}
    no_llm = s.filter(not_tags=["llm"])
    assert {c.id for c in no_llm.cases} == {"ai.sort"}
    only_ai = s.search("ai")
    assert {c.id for c in only_ai.cases} == {"ai.sort", "ai.llm"}


def test_suite_expand_matrix():
    case = Case(
        id="x",
        params={"a": [1, 2], "b": [10, 20, 30]},
    )
    s = Suite(cases=[case])
    out = s.expand()
    assert len(out) == 6
    assert {tuple(c.params[k] for k in ("a", "b")) for c in out} == {
        (1, 10), (1, 20), (1, 30), (2, 10), (2, 20), (2, 30),
    }


def test_suite_tag_index(tmp_path):
    (tmp_path / "a.yaml").write_text("id: a\ntags: [t1, t2]\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("id: b\ntags: [t2]\n", encoding="utf-8")
    s = Suite.load_dir(str(tmp_path))
    idx = s.tag_index()
    assert set(idx.keys()) == {"t1", "t2"}
    assert set(idx["t2"]) == {"a", "b"}
