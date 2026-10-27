"""NSB Middle School Sample-Questions study tool.

Serves 10 questions at a time (toss-up / bonus pairs preserved) with topic,
kind, and format filters plus full-text search. Answers are hidden behind a
Reveal button so they aren't shipped to the client unless requested.

Designed for Streamlit Community Cloud / Hugging Face Spaces hosting.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

import streamlit as st

# ---------------------------- config ----------------------------
PAGE_SIZE = int(os.environ.get("NSB_PAGE_SIZE", 10))
MIN_SECONDS_BETWEEN_PAGES = float(os.environ.get("NSB_MIN_PAGE_INTERVAL", 2.0))
MAX_QS_PER_HOUR = int(os.environ.get("NSB_MAX_QS_PER_HOUR", 400))
DATA_FILE = Path(__file__).parent / "all_questions_classified.jsonl"

TOPIC_ORDER = [
    "Math", "Physics", "Chemistry",
    "Life Sciences", "Earth and Space", "Energy",
]

st.set_page_config(
    page_title="NSB MS – Study Tool",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------- data ----------------------------
@st.cache_data(show_spinner=False)
def load_rows(_mtime: float, _size: int) -> list[dict]:
    """Cache keyed on (file mtime, file size) so a new JSONL invalidates the cache."""
    rows = []
    with DATA_FILE.open() as f:
        for line in f:
            r = json.loads(line)
            r["topic"] = r.get("topic6", r.get("topic"))
            rows.append(r)
    for r in rows:
        s, rd = _parse_set_round(r["source"])
        r["set_label"] = s
        r["round_label"] = rd
    # TOSS-UP then BONUS for each (source, number)
    rows.sort(key=lambda r: (r["source"], r["number"], 0 if r["kind"] == "TOSS-UP" else 1))
    return rows


def _data_cache_key():
    s = DATA_FILE.stat()
    return s.st_mtime, s.st_size


def _parse_set_round(source: str) -> tuple[str, str]:
    parts = source.split("/", 1)
    set_dir = parts[0]
    fname = parts[1] if len(parts) > 1 else ""
    if "Sample-Rounds" in set_dir:
        set_label = "Sample Rounds (Set 13)"
    else:
        m = re.search(r"Sample-[Ss]et-?(\d+)", set_dir)
        set_label = f"Set {m.group(1)}" if m else set_dir
    stem = fname.rsplit(".", 1)[0]
    patterns = [
        (r"[Rr]ound[-_ ]*(\d+[A-Za-z]?)", "Round {}"),
        (r"[Mm]s[_\- ]?[Rr]d[-_]?(\d+[A-Za-z]?)", "Round {}"),
        (r"(\d{1,2}[A-Za-z])_MS", "Round {}"),
        (r"m_round(\d{1,2})", "Round {}"),
        (r"sample_questions_r(\d+)", "Round {}"),
        (r"Set[-_]?(\d+)[-_]MS", "Round {}"),
        (r"MS[-_](\d+)", "Round {}"),
        (r"RegionalMS[-_]?(\d+)", "Round {}"),
        (r"^de(\d)", "Double Elim {}"),
        (r"^rr(\d)", "Round Robin {}"),
        (r"^2022[-_]MS[-_](\d+)", "Round {}"),
        (r"^2024[-_]MS[-_][Rr]ound[-_]?(\d+)", "Round {}"),
    ]
    for pat, fmt in patterns:
        m = re.search(pat, stem)
        if m:
            return set_label, fmt.format(m.group(1).upper())
    return set_label, stem


# ---------------------------- session ----------------------------
if "sid" not in st.session_state:
    st.session_state.sid = uuid.uuid4().hex[:8]
if "page" not in st.session_state:
    st.session_state.page = 1
if "last_page_at" not in st.session_state:
    st.session_state.last_page_at = 0.0
if "seen_log" not in st.session_state:
    st.session_state.seen_log = []  # list of timestamps when questions were served
if "reveal" not in st.session_state:
    st.session_state.reveal = {}  # id -> True

rows = load_rows(*_data_cache_key())

# ---------------------------- sidebar ----------------------------
with st.sidebar:
    st.title("🧪 NSB MS Study")
    st.caption(f"{len(rows):,} questions across all 16 Sample Question Sets")
    st.markdown("---")

    present_topics = ["All"] + [t for t in TOPIC_ORDER if any(r["topic"] == t for r in rows)]
    topic = st.selectbox("Topic", present_topics)

    # Sub-topic dropdown appears only when a specific topic is selected.
    subtopic = "All"
    if topic != "All":
        from collections import Counter
        sub_counts = Counter(r.get("subtopic", "Other / General") for r in rows if r["topic"] == topic)
        sub_options = ["All"] + [f"{name} ({n})" for name, n in sub_counts.most_common()]
        chosen = st.selectbox("Sub-topic", sub_options)
        subtopic = chosen.rsplit(" (", 1)[0] if chosen != "All" else "All"

    kind = st.selectbox("Question type", ["All", "TOSS-UP", "BONUS"])
    fmt = st.selectbox("Format", ["All", "Short Answer", "Multiple Choice"])
    search = st.text_input("Search text (question + answer)", "")

    st.markdown("---")
    st.caption(f"Session **#{st.session_state.sid}**")
    st.caption(f"Served this hour: **{len([t for t in st.session_state.seen_log if time.time()-t<3600])}** / {MAX_QS_PER_HOUR}")

# ---------------------------- filter ----------------------------
q = search.strip().lower()

def match(r: dict) -> bool:
    if topic != "All" and r["topic"] != topic: return False
    if subtopic != "All":
        # A question matches a sub-topic if it's in its `subtopics` list
        # (so a question tagged primarily "Forces & Newton's Laws" also appears
        # in "Mechanics" if it mentions velocity, etc.)
        if subtopic not in r.get("subtopics", [r.get("subtopic", "")]):
            return False
    if kind  != "All" and r["kind"]  != kind:  return False
    if fmt   != "All" and r["format"] != fmt:  return False
    if q:
        hay = (r["question"] + " " + r["answer"] + " " + r["topic"] + " " + r["source"]).lower()
        if q not in hay: return False
    return True

filtered = [r for r in rows if match(r)]
total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
st.session_state.page = min(max(1, st.session_state.page), total_pages)

# ---------------------------- header ----------------------------
st.markdown("## NSB Middle School – Sample Questions")
col1, col2, col3 = st.columns([2,1,1])
col1.markdown(f"**{len(filtered):,}** matching questions · page **{st.session_state.page}** of **{total_pages}** · {PAGE_SIZE} per page")

prev, _, nxt = col2.columns([1,1,1]), None, col3.columns([1,1,1])

cols = st.columns([1,1,1,1])
if cols[0].button("⟵ Prev", disabled=st.session_state.page <= 1):
    st.session_state.page -= 1
if cols[1].button("Next ⟶", disabled=st.session_state.page >= total_pages):
    st.session_state.page += 1
cols[2].number_input(
    "Jump to page", min_value=1, max_value=total_pages,
    value=st.session_state.page, key="jump", label_visibility="collapsed",
    on_change=lambda: setattr(st.session_state, "page", st.session_state.jump),
)
if cols[3].button("🎲 Random page"):
    import random
    st.session_state.page = random.randint(1, total_pages)

# ---------------------------- rate-limit gates ----------------------------
now = time.time()
# interval gate
dt = now - st.session_state.last_page_at
if dt < MIN_SECONDS_BETWEEN_PAGES and st.session_state.last_page_at > 0:
    time.sleep(MIN_SECONDS_BETWEEN_PAGES - dt)

# hourly cap
served_this_hour = len([t for t in st.session_state.seen_log if now - t < 3600])
page_slice = filtered[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]
if served_this_hour + len(page_slice) > MAX_QS_PER_HOUR:
    remaining = max(0, MAX_QS_PER_HOUR - served_this_hour)
    st.warning(
        f"You've viewed {served_this_hour} questions in the last hour "
        f"(limit {MAX_QS_PER_HOUR}). Only showing {remaining} this page. "
        f"Come back later for more."
    )
    page_slice = page_slice[:remaining]

# record what we served
st.session_state.last_page_at = time.time()
st.session_state.seen_log.extend([time.time()] * len(page_slice))
st.session_state.seen_log = [t for t in st.session_state.seen_log if time.time() - t < 3600]

# ---------------------------- render ----------------------------
def render_question(r: dict, idx: int):
    with st.container(border=True):
        meta_bits = [
            f"**{r['topic']}**",
            f"_{r.get('subtopic','Other / General')}_",
            r["set_label"],
            r["round_label"],
            f"{r['kind']} #{r['number']}",
            r["format"],
        ]
        if r.get("category_raw") and r["category_raw"].lower() != r["topic"].lower():
            meta_bits.append(f"orig: `{r['category_raw']}`")
        st.caption(" · ".join(meta_bits))
        st.markdown(r["question"])
        qid = f"{r['source']}|{r['kind']}|{r['number']}"
        if st.session_state.reveal.get(qid):
            st.success(f"**Answer:** {r['answer']}")
        else:
            if st.button("👁 Reveal answer", key=f"rev-{st.session_state.page}-{idx}"):
                st.session_state.reveal[qid] = True
                st.rerun()

prev_round = None
for i, r in enumerate(page_slice):
    round_key = (r["source"], r["set_label"], r["round_label"])
    if round_key != prev_round:
        st.markdown(f"### {r['set_label']} — {r['round_label']}")
        prev_round = round_key
    render_question(r, i)

# ---------------------------- footer / watermark ----------------------------
st.markdown("---")
st.caption(
    f"Session {st.session_state.sid} · "
    f"{time.strftime('%Y-%m-%d %H:%M:%S')} · "
    f"page {st.session_state.page}/{total_pages} · "
    f"source PDFs: science.osti.gov NSB Middle-School Sample Questions"
)

# ---------------------------- deterrents (JS) ----------------------------
# Block Ctrl+P / Ctrl+S / right-click. Deterrent only; screenshots still work.
st.markdown(
    """
    <style>
      @media print { body { display: none !important; } }
    </style>
    <script>
      document.addEventListener('contextmenu', e => e.preventDefault());
      document.addEventListener('keydown', e => {
        const k = (e.key || '').toLowerCase();
        if ((e.metaKey || e.ctrlKey) && (k === 'p' || k === 's' || k === 'u')) {
          e.preventDefault();
        }
      });
    </script>
    """,
    unsafe_allow_html=True,
)
