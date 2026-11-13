"""Shared config loading for the linkedin-jobs skill. No personal data lives in this file."""
from __future__ import annotations

import json
import os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

DEFAULTS: dict = {
    # Where the persistent (signed-in) browser profile lives. Keep it OUTSIDE any git repo.
    "profile_dir": str(Path.home() / ".linkedin-jobs-skill" / "profile"),
    # null = Playwright's bundled Chromium (recommended). Or a path to opera.exe / chrome.exe / etc.
    "browser_path": None,
    "location": "Germany",
    "job_type": "F",  # LinkedIn f_JT: F=full-time, C=contract, P=part-time, I=internship
    "hours": 24,
    "max_pages": 1,
    # lane name -> {"keywords": [search terms], "title_regex": optional regex a result title must match}
    "lanes": {},
    # Titles matching this regex are dropped.
    "exclude_title_regex": r"\b(intern|internship|working student|werkstudent|praktikum|trainee|junior|"
                           r"freelance|contract|apprentice|ausbildung|thesis)\b",
    # Optional text file holding already-seen job ids (matched by seen_id_regex) for dedup.
    "seen_file": None,
    "seen_id_regex": r"linkedin:(\d+)",
    "output": "linkedin-candidates.json",
    "fetch_details": True,
}


def load_config(path: str | None = None) -> dict:
    candidates = [path, os.environ.get("LINKEDIN_SKILL_CONFIG"),
                  "linkedin-jobs.config.json", str(SKILL_ROOT / "config.json")]
    cfg = dict(DEFAULTS)
    for c in candidates:
        if c and Path(c).is_file():
            cfg.update(json.loads(Path(c).read_text(encoding="utf-8")))
            cfg["_config_path"] = str(Path(c).resolve())
            break
    return cfg
