import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import linkedin_search as ls  # noqa: E402
from li_config import DEFAULTS, load_config  # noqa: E402

CFG = {**DEFAULTS, "lanes": {
    "AI": {"keywords": ["AI Engineer", "LLM Engineer"]},
    "Backend": {"keywords": ["Backend Engineer"], "title_regex": r"\b(backend|staff|principal)\b"},
}}


def test_job_id_from_url():
    assert ls.job_id_from_url("https://www.linkedin.com/jobs/view/4012345678/?refId=x") == "4012345678"
    assert ls.job_id_from_url("/jobs/view/senior-engineer-at-acme-4012345678?trk=a") == "4012345678"
    assert ls.job_id_from_url("https://www.linkedin.com/feed/") is None


def test_lanes_use_keywords_or_regex_and_exclusions():
    assert ls.lanes_for_title("Senior AI Engineer (m/f/d)", CFG) == ["AI"]
    assert ls.lanes_for_title("Staff Software Engineer", CFG) == ["Backend"]
    assert ls.lanes_for_title("Marketing Manager", CFG) == []
    assert ls.lanes_for_title("Working Student AI Engineer", CFG) == []


def test_company_from_page_title():
    assert ls.company_from_title("Founding Engineer | Acme GmbH | LinkedIn") == "Acme GmbH"
    assert ls.company_from_title("LinkedIn") == ""


def test_seen_ids(tmp_path):
    f = tmp_path / "seen.md"
    f.write_text("| x | linkedin:4012345678 |\n| y | other:foo-1 |\n", encoding="utf-8")
    assert ls.seen_ids(str(f), r"linkedin:(\d+)") == {"4012345678"}
    assert ls.seen_ids(None, r"x") == set()
    assert ls.seen_ids(str(tmp_path / "missing"), r"x") == set()


def test_build_candidates_filters_and_dedups():
    cards = [
        {"id": "1", "title": "Senior AI Engineer", "company": "A", "location": "", "url": "u1"},
        {"id": "1", "title": "Senior AI Engineer", "company": "A", "location": "", "url": "u1"},
        {"id": "2", "title": "Marketing Manager", "company": "B", "location": "", "url": "u2"},
        {"id": "3", "title": "Staff Engineer", "company": "C", "location": "", "url": "u3"},
    ]
    out = ls.build_candidates(cards, {"3"}, CFG)
    assert [c["id"] for c in out] == ["1"] and out[0]["lanes"] == ["AI"]


def test_load_config_merges_over_defaults(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"location": "Austria", "lanes": {"X": {"keywords": ["a"]}}}', encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg["location"] == "Austria" and cfg["job_type"] == "F" and "X" in cfg["lanes"]
