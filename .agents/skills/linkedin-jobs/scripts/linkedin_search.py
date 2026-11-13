#!/usr/bin/env python
"""Read-only LinkedIn job search -> pre-filtered candidates JSON.

    python scripts/linkedin_search.py [--config path] [--hours N] [--max-pages N]
                                      [--out file] [--no-details] [--seen-file file]

Needs a signed-in profile (run linkedin_login.py first). Read-only: never applies, messages
or connects. Human-paced (random delays, small page counts). Stops at the first LinkedIn
checkpoint/CAPTCHA/login wall. Output: JSON list of
{id, title, company, location, url, lanes, header, description}; location lives in header[2]
on current LinkedIn pages. Scoring against a CV is left to the calling agent.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

from li_config import load_config

BLOCK_URL = re.compile(r"(checkpoint|authwall|/login|/uas/|captcha)", re.I)
NOISE_LINES = {"easy apply", "promoted", "viewed", "new"}


# --- pure logic (unit-tested) ---------------------------------------------------------------

def job_id_from_url(url: str) -> str | None:
    m = re.search(r"/jobs/view/(?:[^/?]*?-)?(\d{6,})", url)
    return m.group(1) if m else None


def lanes_for_title(title: str, cfg: dict) -> list[str]:
    if cfg.get("exclude_title_regex") and re.search(cfg["exclude_title_regex"], title, re.I):
        return []
    out = []
    for lane, spec in cfg["lanes"].items():
        rx = spec.get("title_regex") or "|".join(re.escape(k) for k in spec["keywords"])
        if re.search(rx, title, re.I):
            out.append(lane)
    return out


def company_from_title(page_title: str) -> str:
    parts = [p.strip() for p in page_title.split("|")]
    return parts[1] if len(parts) >= 3 and parts[-1].lower() == "linkedin" else ""


def seen_ids(path: str | None, id_regex: str) -> set[str]:
    if not path or not Path(path).is_file():
        return set()
    return set(re.findall(id_regex, Path(path).read_text(encoding="utf-8")))


def build_candidates(cards: list[dict], seen: set[str], cfg: dict) -> list[dict]:
    out, ids = [], set(seen)
    for c in cards:
        if c["id"] in ids:
            continue
        lanes = lanes_for_title(c["title"], cfg)
        if not lanes:
            continue
        ids.add(c["id"])
        out.append({**c, "lanes": lanes})
    return out


def parse_card(row: dict) -> dict | None:
    jid = job_id_from_url(row["url"])
    lines = [l for l in row["lines"] if l.lower() not in NOISE_LINES]
    if not jid or not lines:
        return None
    title = lines[0]
    rest = [l for l in lines[1:] if l != title and not l.startswith(title)]  # LinkedIn repeats the title
    return {"id": jid, "title": title, "company": rest[0] if rest else "",
            "location": rest[1] if len(rest) > 1 else "", "url": f"https://www.linkedin.com/jobs/view/{jid}/"}


# --- browser part (depends on LinkedIn's live DOM; may need selector upkeep) ----------------

CARD_JS = """
() => {
  const seen = new Set(), rows = [];
  for (const a of document.querySelectorAll('a[href*="/jobs/view/"]')) {
    const href = a.href.split('?')[0];
    if (seen.has(href)) continue;
    seen.add(href);
    const li = a.closest('li') || a.closest('[data-job-id]') || a.parentElement;
    const lines = (li ? li.innerText : a.innerText).split('\\n').map(s => s.trim()).filter(Boolean);
    rows.push({url: href, lines});
  }
  return rows;
}
"""

DETAIL_JS = """
() => {
  const el = document.querySelector('#job-details, .jobs-description, article') || document.body;
  const top = (document.querySelector('main') || document.body).innerText.split('\\n')
      .map(s => s.trim()).filter(Boolean).slice(0, 15);
  return {title: document.title, header: top, description: el.innerText.slice(0, 8000)};
}
"""


def pause(a: float = 2.5, b: float = 6.0) -> None:
    time.sleep(random.uniform(a, b))


def walled(page) -> bool:
    if BLOCK_URL.search(page.url):
        print(f"STOP: LinkedIn wall at {page.url}. Resolve it in the browser, then rerun.", file=sys.stderr)
        return True
    return False


def enrich(page, cands: list[dict]) -> None:
    for c in cands:
        page.goto(c["url"], wait_until="domcontentloaded")
        pause(3, 7)
        if walled(page):
            return
        d = page.evaluate(DETAIL_JS)
        c["company"] = company_from_title(d["title"]) or c["company"]
        c["header"] = d["header"]
        c["description"] = d["description"]


def search(cfg: dict, seen: set[str]) -> list[dict]:
    from playwright.sync_api import sync_playwright
    cards: list[dict] = []
    kwargs = {"executable_path": cfg["browser_path"]} if cfg["browser_path"] else {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(cfg["profile_dir"], headless=False,
                                                   viewport={"width": 1280, "height": 900}, **kwargs)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for lane, spec in cfg["lanes"].items():
                for kw in spec["keywords"]:
                    for pg in range(cfg["max_pages"]):
                        url = ("https://www.linkedin.com/jobs/search/?keywords=" + quote_plus(kw) +
                               "&location=" + quote_plus(cfg["location"]) +
                               "&f_TPR=r" + str(int(cfg["hours"]) * 3600) +
                               "&f_JT=" + cfg["job_type"] + "&sortBy=DD&start=" + str(pg * 25))
                        page.goto(url, wait_until="domcontentloaded")
                        pause()
                        if walled(page):
                            return build_candidates(cards, seen, cfg)
                        for _ in range(4):  # lazy-loaded result list
                            page.mouse.wheel(0, 1500)
                            pause(0.8, 1.6)
                        found = [c for c in (parse_card(r) for r in page.evaluate(CARD_JS)) if c]
                        print(f"[{lane}] '{kw}' page {pg + 1}: {len(found)} cards")
                        cards += found
                        if len(found) < 10:
                            break
            cands = build_candidates(cards, seen, cfg)
            print(f"{len(cards)} cards -> {len(cands)} candidates after filter/dedup")
            if cfg["fetch_details"]:
                enrich(page, cands)
            return cands
        finally:
            ctx.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--hours", type=int)
    ap.add_argument("--max-pages", type=int)
    ap.add_argument("--out")
    ap.add_argument("--seen-file")
    ap.add_argument("--no-details", action="store_true")
    a = ap.parse_args()
    cfg = load_config(a.config)
    for k, v in (("hours", a.hours), ("max_pages", a.max_pages), ("output", a.out), ("seen_file", a.seen_file)):
        if v is not None:
            cfg[k] = v
    if a.no_details:
        cfg["fetch_details"] = False
    if not cfg["lanes"]:
        sys.exit("No 'lanes' configured. Copy config.example.json to linkedin-jobs.config.json and edit it.")
    cands = search(cfg, seen_ids(cfg["seen_file"], cfg["seen_id_regex"]))
    Path(cfg["output"]).write_text(json.dumps(cands, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(cands)} new candidates -> {cfg['output']}")


if __name__ == "__main__":
    main()
