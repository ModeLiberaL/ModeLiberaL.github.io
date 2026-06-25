"""Build compact ACL/AAAI/ICML/ICLR 2026 paper indexes from official sources."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
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


def clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1-\2", text)


def has_term(text: str, term: str) -> bool:
    if term.startswith("re:"):
        return re.search(term[3:], text) is not None
    if len(term) <= 3 and term.replace("-", "").isalpha():
        return re.search(rf"\b{re.escape(term)}\b", text) is not None
    return term in text


def classify_title(title: str, rules: tuple[tuple[str, tuple[str, ...]], ...], default: str) -> str:
    haystack = title.casefold()
    for group, terms in rules:
        if any(has_term(haystack, term) for term in terms):
            return group
    return default


ACL_TOPIC_RULES = (
    (
        "可信、安全与社会影响",
        (
            "safety",
            "bias",
            "fairness",
            "privacy",
            "toxic",
            "toxicity",
            "harm",
            "jailbreak",
            "attack",
            "defense",
            "red team",
            "misinformation",
            "moderation",
            "stereotype",
            "ethic",
            "watermark",
            "robust",
            "guardrail",
        ),
    ),
    (
        "推理、可解释性与评测",
        (
            "reasoning",
            "chain-of-thought",
            "cot",
            "mathematical",
            "symbolic",
            "logic",
            "explain",
            "interpret",
            "faithfulness",
            "hallucination",
            "evaluation",
            "benchmark",
            "assess",
            "probing",
            "probe",
            "calibration",
            "uncertainty",
            "verification",
            "factual",
        ),
    ),
    (
        "多模态、语音与具身",
        (
            "multimodal",
            "multi-modal",
            "vision-language",
            "visual",
            "image",
            "video",
            "speech",
            "spoken",
            "audio",
            "robot",
            "embodied",
            "grounding",
            "gesture",
        ),
    ),
    (
        "多语言、翻译与低资源",
        (
            "multilingual",
            "cross-lingual",
            "translation",
            "machine translation",
            "low-resource",
            "low resource",
            "code-switch",
            "dialect",
            "language diversity",
            "morphology",
        ),
    ),
    (
        "检索、知识与问答",
        (
            "retrieval",
            "retriever",
            "rag",
            "retrieval-augmented",
            "question answering",
            "qa",
            "knowledge graph",
            "knowledge base",
            "entity",
            "relation extraction",
            "fact-check",
            "citation",
        ),
    ),
    (
        "生成、对话与摘要",
        (
            "generation",
            "generative",
            "summarization",
            "summary",
            "dialogue",
            "dialog",
            "conversation",
            "chat",
            "caption",
            "paraphrase",
            "story",
        ),
    ),
    (
        "LLM、Agent 与基础模型",
        (
            "large language",
            "llm",
            "gpt",
            "language model",
            "foundation model",
            "pre-trained",
            "pretrained",
            "instruction",
            "prompt",
            "agent",
            "multi-agent",
            "tool use",
            "tool-use",
            "in-context",
            "fine-tuning",
            "finetuning",
            "preference optimization",
            "post-training",
        ),
    ),
    (
        "语言结构、信息抽取与资源",
        (
            "syntax",
            "parsing",
            "semantic",
            "discourse",
            "pragmatic",
            "phonology",
            "information extraction",
            "named entity",
            "dataset",
            "corpus",
            "annotation",
            "resource",
            "tokenization",
            "taxonomy",
            "classification",
        ),
    ),
)

ACL_TOPIC_DEFAULT = "领域应用与其他 NLP"
ACL_TOPIC_ORDER = tuple(group for group, _ in ACL_TOPIC_RULES) + (ACL_TOPIC_DEFAULT,)


def classify_acl_topic(title: str) -> str:
    return classify_title(title, ACL_TOPIC_RULES, ACL_TOPIC_DEFAULT)


AAAI_TOPIC_RULES = (
    (
        "可信 AI、安全与对齐",
        (
            "safety",
            "privacy",
            "fairness",
            "bias",
            "attack",
            "defense",
            "jailbreak",
            "watermark",
            "robust",
            "trustworthy",
            "hallucination",
            "adversarial",
            "governance",
            "oversight",
            "incident",
            "harm",
            "preference optimization",
            "rlhf",
        ),
    ),
    (
        "AI 应用：健康、科学与社会影响",
        (
            "medical",
            "clinical",
            "health",
            "medicine",
            "protein",
            "drug",
            "molecule",
            "chem",
            "biology",
            "ecg",
            "cancer",
            "disease",
            "energy",
            "climate",
            "weather",
            "traffic",
            "urban",
            "education",
            "agriculture",
            "disaster",
            "wildfire",
            "social good",
            "public",
            "finance",
            "trading",
            "material",
            "battery",
            "robotics: emerging",
        ),
    ),
    (
        "计算机视觉与多模态",
        (
            "image",
            "video",
            "visual",
            "vision",
            "multimodal",
            "multi-modal",
            "3d",
            "point cloud",
            "lidar",
            "object detection",
            "segmentation",
            "pose",
            "gaussian splatting",
            "diffusion",
            "captioning",
            "face",
            "audio-language",
        ),
    ),
    (
        "语言模型、NLP 与 Agent",
        (
            "large language",
            "llm",
            "language model",
            "natural language",
            "nlp",
            "text",
            "prompt",
            "rag",
            "retrieval",
            "question answering",
            "dialogue",
            "code",
            "agent",
            "web agent",
            "tool",
            "translation",
        ),
    ),
    (
        "强化学习、规划与机器人",
        (
            "reinforcement learning",
            "offline rl",
            "rl agent",
            "policy",
            "planning",
            "control",
            "robot",
            "navigation",
            "manipulation",
            "autonomous",
            "game",
            "multi-agent reinforcement",
            "decision-making",
        ),
    ),
    (
        "数据挖掘、图学习与推荐",
        (
            "graph",
            "network",
            "recommender",
            "recommendation",
            "clustering",
            "mining",
            "time series",
            "forecasting",
            "spatiotemporal",
            "spatio-temporal",
            "anomaly",
            "knowledge graph",
        ),
    ),
    (
        "知识表示、推理与搜索",
        (
            "reasoning",
            "logic",
            "symbolic",
            "neuro-symbolic",
            "knowledge",
            "search",
            "causal",
            "counterfactual",
            "explain",
            "interpret",
            "shap",
            "proof",
            "formal",
            "metacognition",
        ),
    ),
    (
        "数据集、评测、系统与基准",
        (
            "benchmark",
            "dataset",
            "evaluation",
            "survey",
            "review",
            "platform",
            "system",
            "simulator",
            "simulation",
            "challenge",
            "empirical",
            "framework",
        ),
    ),
)

AAAI_TOPIC_DEFAULT = "机器学习、优化与理论"
AAAI_TOPIC_ORDER = tuple(group for group, _ in AAAI_TOPIC_RULES) + (AAAI_TOPIC_DEFAULT,)


def classify_aaai_topic(title: str) -> str:
    return classify_title(title, AAAI_TOPIC_RULES, AAAI_TOPIC_DEFAULT)


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
                    "g": classify_acl_topic(title),
                    "c": group,
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
            ACL_TOPIC_ORDER.index(paper["g"]),
            next(index for index, section in enumerate(ACL_SECTIONS) if section[2] == paper["d"]),
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


AAAI_PAPER_ID_RE = re.compile(r"\b(?:AISI|AIA|ETA)?\d+\b")
AAAI_WEEKDAY_RE = re.compile(r"^(?:Thursday|Friday|Saturday|Sunday|Monday),")

AAAI_SOURCES = (
    (
        "Main Technical Track",
        "Main",
        "Oral",
        "oral",
        "https://aaai.org/2026-main-track-presentations/",
    ),
    (
        "Main Technical Track",
        "Main",
        "Poster",
        "poster",
        "https://aaai.org/2026-main-track-posters/",
    ),
    (
        "AI for Social Impact",
        "AISI",
        "Oral",
        "oral",
        "https://aaai.org/2026-ai-for-social-impact-presentations/",
    ),
    (
        "AI for Social Impact",
        "AISI",
        "Poster",
        "poster",
        "https://aaai.org/2026-ai-for-social-impact-posters/",
    ),
    (
        "AI Alignment",
        "AIA",
        "Oral",
        "oral",
        "https://aaai.org/2026-ai-alignment-presentations/",
    ),
    (
        "AI Alignment",
        "AIA",
        "Poster",
        "poster",
        "https://aaai.org/2026-ai-alignment-posters/",
    ),
    (
        "Emerging Trends in AI",
        "ETA",
        "Oral",
        "oral",
        "https://aaai.org/wp-content/uploads/2025/12/ETA-track-oral-talks_20251202.pdf",
    ),
)


def get_bytes(url: str, *, attempts: int = 5) -> bytes:
    for attempt in range(attempts):
        response = SESSION.get(url, timeout=120)
        if response.status_code == 200:
            return response.content
        if response.status_code in {429, 500, 502, 503, 504}:
            wait = int(response.headers.get("Retry-After", 2 + attempt * 2))
            time.sleep(min(wait, 20))
            continue
        response.raise_for_status()
    raise RuntimeError(f"Unable to fetch {url} after {attempts} attempts")


def pdf_text_from_url(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "source.pdf"
        txt_path = Path(tmpdir) / "source.txt"
        pdf_path.write_bytes(get_bytes(url))
        subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
            check=True,
            capture_output=True,
        )
        return txt_path.read_text(encoding="utf-8", errors="ignore")


def split_pdf_columns(line: str, title_start: int, authors_start: int) -> tuple[str, str]:
    title = line[title_start:authors_start].strip() if len(line) > title_start else ""
    authors = line[authors_start:].strip() if len(line) > authors_start else ""
    return title, authors


def text_start_after_match(line: str, match: re.Match, fallback: int) -> int:
    index = match.end()
    while index < len(line) and line[index].isspace():
        index += 1
    if index < len(line) and index < fallback + 4:
        return index
    return fallback


def parse_aaai_oral_text(text: str) -> list[dict]:
    lines = text.splitlines()
    header = next(
        line
        for line in lines
        if "Paper ID" in line and "Paper Title" in line and "Authors" in line
    )
    id_start = header.index("Paper ID")
    title_start = header.index("Paper Title")
    authors_start = header.index("Authors")
    records = []
    current = None

    for raw_line in lines:
        line = raw_line.replace("\x0c", "")
        if not line.strip() or ("Paper ID" in line and "Paper Title" in line):
            continue
        match = AAAI_PAPER_ID_RE.search(line[max(0, id_start - 4) : title_start])
        if match:
            if current:
                records.append(current)
            title_start_current = text_start_after_match(
                line,
                match,
                title_start,
            )
            title, authors = split_pdf_columns(line, title_start_current, authors_start)
            current = {
                "id": match.group(0),
                "title_start": title_start_current,
                "title": [title],
                "authors": [authors],
            }
            continue
        if current:
            title, authors = split_pdf_columns(line, current["title_start"], authors_start)
            if title:
                current["title"].append(title)
            if authors:
                current["authors"].append(authors)

    if current:
        records.append(current)
    return records


def parse_aaai_poster_text(text: str) -> list[dict]:
    lines = text.splitlines()
    header = next(
        line for line in lines if "Board" in line and "Paper Title" in line and "Authors" in line
    )
    board_start = header.index("Board")
    title_start = header.index("Paper Title")
    authors_start = header.index("Authors")
    records = []
    current = None

    for raw_line in lines:
        line = raw_line.replace("\x0c", "")
        if not line.strip() or ("Paper Title" in line and "Authors" in line):
            continue
        if AAAI_WEEKDAY_RE.match(line):
            if current:
                records.append(current)
            board = clean_text(line[board_start:title_start]).split(" ")[0]
            title, authors = split_pdf_columns(line, title_start, authors_start)
            current = {
                "id": board,
                "title": [title],
                "authors": [authors],
            }
            continue
        if current:
            title, authors = split_pdf_columns(line, title_start, authors_start)
            if title:
                current["title"].append(title)
            if authors:
                current["authors"].append(authors)

    if current:
        records.append(current)
    return records


def build_aaai() -> dict:
    source_records = 0
    merged = {}
    source_counts = {}

    for track_name, track_code, presentation, parser_kind, url in AAAI_SOURCES:
        text = pdf_text_from_url(url)
        parsed = (
            parse_aaai_oral_text(text)
            if parser_kind == "oral"
            else parse_aaai_poster_text(text)
        )
        source_counts[f"{track_code} {presentation}"] = len(parsed)
        source_records += len(parsed)
        print(f"AAAI {track_code} {presentation}: {len(parsed):,}")

        for paper in parsed:
            title = clean_text(" ".join(paper["title"]))
            authors = clean_text(" ".join(paper["authors"]))
            if not title or not authors:
                continue
            record = {
                "t": title,
                "a": clean_authors([name.strip() for name in authors.split(";") if name.strip()]),
                "g": "可信 AI、安全与对齐"
                if track_code == "AIA"
                else classify_aaai_topic(title),
                "c": track_name,
                "d": track_code,
                "e": presentation,
                "k": [f"ID {paper['id']}"] if paper.get("id") else [],
                "u": url,
                "v": "",
                "l": "官方 PDF ↗",
            }
            key = (title.casefold(), record["a"].casefold())
            existing = merged.get(key)
            if not existing:
                merged[key] = record
                continue
            if existing["e"] == "Poster" and presentation == "Oral":
                record["v"] = existing["u"] if existing["u"] != url else existing.get("v", "")
                merged[key] = record
            elif existing["u"] != url and not existing.get("v"):
                existing["v"] = url

    records = list(merged.values())
    records.sort(
        key=lambda paper: (
            AAAI_TOPIC_ORDER.index(paper["g"]),
            0 if paper["e"] == "Oral" else 1,
            paper["d"],
            paper["t"].casefold(),
        )
    )
    return {
        "conference": "AAAI 2026",
        "updated": UPDATED,
        "source": "https://aaai.org/conference/aaai/aaai-26/main-technical-track/",
        "source_records": source_records,
        "duplicates_removed": source_records - len(records),
        "source_counts": source_counts,
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
    write_payload("aaai-2026-papers.json", build_aaai())
    write_payload("icml-2026-papers.json", build_icml())
    write_payload("iclr-2026-papers.json", build_iclr())
