"""Build compact ACL/ICML/ICLR 2026 paper indexes from official sources."""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
UPDATED = "2026-06-25"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "Accept": "application/json",
        "User-Agent": "ModeLiberaL-Research-Atlas/1.0",
    }
)


def get_json(url: str, *, params: dict | None = None, attempts: int = 8):
    for attempt in range(attempts):
        response = SESSION.get(url, params=params, timeout=120)
        if response.status_code == 200:
            return response.json()
        if response.status_code in {429, 500, 502, 503, 504}:
            wait = int(response.headers.get("Retry-After", 2 + attempt * 2))
            time.sleep(min(wait, 20))
            continue
        response.raise_for_status()
    raise RuntimeError(f"Unable to fetch {url} after {attempts} attempts")


def clean_authors(names: list[str]) -> str:
    return "、".join(name.strip() for name in names if name and name.strip())


def clean_keywords(values) -> list[str]:
    if not isinstance(values, list):
        return []
    result = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result[:8]


ACL_SECTIONS = (
    (
        "主会论文",
        "Main Conference",
        "Main",
        "https://2026.aclweb.org/program/accepted_papers/",
    ),
    (
        "Findings",
        "Findings of ACL",
        "Findings",
        "https://2026.aclweb.org/program/findings/",
    ),
    (
        "产业论文",
        "Industry Track",
        "Industry",
        "https://2026.aclweb.org/program/industry/",
    ),
    (
        "系统演示",
        "System Demonstrations",
        "Demo",
        "https://2026.aclweb.org/program/demo/",
    ),
    (
        "Computational Linguistics",
        "Computational Linguistics Papers",
        "CL",
        "https://2026.aclweb.org/program/cl_papers/",
    ),
    (
        "TACL",
        "Transactions of the ACL Papers",
        "TACL",
        "https://2026.aclweb.org/program/tacl_papers/",
    ),
    (
        "学生研究工作坊",
        "Student Research Workshop",
        "SRW",
        "https://2026.aclweb.org/program/srw_papers/",
    ),
)


def build_acl() -> dict:
    records = []
    for group, category, section_type, url in ACL_SECTIONS:
        response = SESSION.get(url, timeout=120)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        section_records = []
        for item in soup.select("main li, article li, .content li"):
            paragraph = item.find("p")
            if not paragraph or not paragraph.find("br"):
                continue
            title_parts = []
            author_parts = []
            after_break = False
            for node in paragraph.descendants:
                if getattr(node, "name", None) == "br":
                    after_break = True
                elif isinstance(node, NavigableString):
                    target = author_parts if after_break else title_parts
                    target.append(str(node))
            if (
                not paragraph.find("strong")
                and len(title_parts) >= 3
                and title_parts[0].lstrip().startswith("*")
                and title_parts[-1].strip() == "*"
            ):
                title = (
                    title_parts[0].strip().lstrip("*")
                    + "*"
                    + "".join(title_parts[1:-1])
                ).strip()
            else:
                title = "".join(title_parts).strip().strip("*").strip()
            author_text = "".join(author_parts).strip().strip("*").strip()
            if not title or not author_text:
                continue
            authors = "、".join(
                name.strip()
                for name in author_text.split(",")
                if name.strip()
            )
            section_records.append(
                {
                    "t": title,
                    "a": authors,
                    "g": group,
                    "c": category,
                    "d": section_type,
                    "e": "",
                    "k": [],
                    "u": url,
                    "v": "",
                    "l": "官方论文列表 ↗",
                }
            )
        records.extend(section_records)
        print(f"ACL {section_type}: {len(section_records):,}")

    source_record_count = len(records)
    seen = set()
    unique_records = []
    for paper in records:
        identity = (paper["d"], paper["t"].casefold(), paper["a"].casefold())
        if identity in seen:
            continue
        seen.add(identity)
        unique_records.append(paper)
    records = unique_records

    records.sort(
        key=lambda paper: (
            next(
                index
                for index, section in enumerate(ACL_SECTIONS)
                if section[2] == paper["d"]
            ),
            paper["t"].casefold(),
        )
    )
    return {
        "conference": "ACL 2026",
        "updated": UPDATED,
        "source": "https://2026.aclweb.org/program/",
        "source_records": source_record_count,
        "duplicates_removed": source_record_count - len(records),
        "papers": records,
    }


ICML_GROUPS = {
    "Deep Learning": "深度学习",
    "Applications": "应用",
    "General Machine Learning": "通用机器学习",
    "Social Aspects": "社会与可信议题",
    "Theory": "理论",
    "Reinforcement Learning": "强化学习",
    "Optimization": "优化",
    "Probabilistic Methods": "概率方法",
    "Other": "其他与特殊赛道",
}


def build_icml() -> dict:
    payload = get_json(
        "https://icml.cc/static/virtual/data/icml-2026-orals-posters.json"
    )
    all_items = payload["results"]
    items_by_id = {item.get("id"): item for item in all_items}
    records = []
    for item in all_items:
        decision = str(item.get("decision") or "")
        if item.get("eventtype") != "Poster" or not decision.startswith("Accept"):
            continue

        topic = item.get("topic") or "Other"
        group_en, _, detail = topic.partition("->")
        group = ICML_GROUPS.get(group_en, group_en)
        authors = [
            author.get("fullname", "")
            for author in item.get("authors", [])
            if isinstance(author, dict)
        ]
        paper_url = item.get("paper_url") or ""
        virtual_url = item.get("virtualsite_url") or ""
        event_type = "Poster"
        for related_id in item.get("related_events_ids", []):
            related = items_by_id.get(related_id)
            if related and related.get("eventtype") == "Oral":
                event_type = "Oral"
                virtual_url = related.get("virtualsite_url") or virtual_url
                break
        if virtual_url.startswith("/"):
            virtual_url = f"https://icml.cc{virtual_url}"

        records.append(
            {
                "t": str(item.get("name") or "").strip(),
                "a": clean_authors(authors),
                "g": group,
                "c": detail or group_en,
                "d": (
                    "Spotlight"
                    if "spotlight" in decision.lower()
                    else "Regular"
                    if "regular" in decision.lower()
                    else "Poster"
                ),
                "e": event_type,
                "k": clean_keywords(item.get("keywords")),
                "u": paper_url,
                "v": virtual_url,
            }
        )

    records.sort(
        key=lambda paper: (
            paper["g"],
            0 if paper["e"] == "Oral" else 1,
            paper["t"].casefold(),
        )
    )
    return {
        "conference": "ICML 2026",
        "updated": UPDATED,
        "source": "https://icml.cc/virtual/2026/papers.html",
        "papers": records,
    }


ICLR_GROUPS = {
    "foundation or frontier models, including LLMs": "基础/前沿模型（含 LLM）",
    "applications to computer vision, audio, language, and other modalities": "视觉/音频/语言等应用",
    "generative models": "生成模型",
    "datasets and benchmarks": "数据集与基准",
    "alignment, fairness, safety, privacy, and societal considerations": "对齐/安全/公平/隐私",
    "reinforcement learning": "强化学习",
    "unsupervised, self-supervised, semi-supervised, and supervised representation learning": "表征学习",
    "applications to physical sciences (physics, chemistry, biology, etc.)": "物理科学应用",
    "interpretability and explainable AI": "可解释 AI",
    "optimization": "优化",
    "learning theory": "学习理论",
    "applications to robotics, autonomy, planning": "机器人/自主/规划",
    "other topics in machine learning (i.e., none of the above)": "其他机器学习主题",
    "probabilistic methods (Bayesian methods, variational inference, sampling, UQ, etc.)": "概率方法",
    "transfer learning, meta learning, and lifelong learning": "迁移/元/终身学习",
    "learning on graphs and other geometries & topologies": "图与几何拓扑学习",
    "applications to neuroscience & cognitive science": "神经/认知科学应用",
    "learning on time series and dynamical systems": "时间序列与动力系统",
    "causal reasoning": "因果推理",
    "neurosymbolic & hybrid AI systems (physics-informed, logic & formal reasoning, etc.)": "神经符号/混合 AI",
    "infrastructure, software libraries, hardware, systems, etc.": "基础设施/软硬件",
}


def build_iclr() -> dict:
    notes = []
    offset = 0
    while True:
        payload = get_json(
            "https://api2.openreview.net/notes",
            params={
                "content.venueid": "ICLR.cc/2026/Conference",
                "limit": 1000,
                "offset": offset,
            },
        )
        page = payload.get("notes", [])
        notes.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
        time.sleep(0.6)

    records = []
    for note in notes:
        content = note["content"]
        area = content["primary_area"]["value"]
        venue = content["venue"]["value"]
        records.append(
            {
                "t": content["title"]["value"].strip(),
                "a": clean_authors(content["authors"]["value"]),
                "g": ICLR_GROUPS.get(area, area),
                "c": area,
                "d": "Oral" if venue.endswith("Oral") else "Poster",
                "e": "Oral" if venue.endswith("Oral") else "Poster",
                "k": clean_keywords(content.get("keywords", {}).get("value", [])),
                "u": f"https://openreview.net/forum?id={note['id']}",
                "v": "",
            }
        )

    records.sort(
        key=lambda paper: (
            paper["g"],
            0 if paper["d"] == "Oral" else 1,
            paper["t"].casefold(),
        )
    )
    return {
        "conference": "ICLR 2026",
        "updated": UPDATED,
        "source": "https://openreview.net/group?id=ICLR.cc/2026/Conference",
        "papers": records,
    }


def write_payload(filename: str, payload: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"{path.name}: {len(payload['papers']):,} papers, {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    write_payload("acl-2026-papers.json", build_acl())
    write_payload("icml-2026-papers.json", build_icml())
    write_payload("iclr-2026-papers.json", build_iclr())
