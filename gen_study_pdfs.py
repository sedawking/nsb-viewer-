"""Generate per-subtopic PDF study packets.

For each (topic, subtopic) in the requested major topics, produces a PDF
with:
    - Cover page (topic, subtopic, question count, generation date)
    - Section 1: QUESTIONS (toss-up / bonus pairs preserved, no answers,
                 MC options shown as W/X/Y/Z)
    - Section 2: ANSWER KEY (same numbering)

Writes to ./study_packs/<Topic>/<NN>_<SubtopicSlug>.pdf
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).parent
DATA = ROOT / "all_questions_classified.jsonl"
OUT = ROOT / "study_packs"
OUT.mkdir(exist_ok=True)

TARGET_TOPICS = ["Physics", "Energy"]

# ---------- utils ----------

CHOICE_SPLIT = re.compile(r"\n\s*([WXYZ])\)\s*", re.IGNORECASE)


def parse_mc(question_text: str) -> tuple[str, list[tuple[str, str]]]:
    parts = CHOICE_SPLIT.split(question_text)
    stem = parts[0].strip()
    choices = []
    for i in range(1, len(parts) - 1, 2):
        letter = parts[i].upper()
        text = parts[i + 1].strip()
        choices.append((letter, text))
    return stem, choices


def ascii_safe(s: str) -> str:
    """Transliterate / strip chars that can't be encoded in latin-1 (default PDF font)."""
    if not s:
        return ""
    # Common smart punctuation
    tbl = {
        "\u2018": "'", "\u2019": "'", "\u201C": '"', "\u201D": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...",
        "\u00b0": " deg", "\u00b2": "^2", "\u00b3": "^3",
        "\u00bd": "1/2", "\u00bc": "1/4", "\u00be": "3/4",
        "\u00d7": "x", "\u00f7": "/", "\u2212": "-", "\u00b1": "+/-",
        "\u221a": "sqrt", "\u03bc": "u", "\u03c0": "pi",
        "\u00b7": ".", "\u2022": "*", "\u2032": "'", "\u2033": '"',
        "\u2192": "->", "\u2190": "<-", "\u2194": "<->",
        "\u00a9": "(c)", "\u00ae": "(r)", "\u2122": "(tm)",
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e",
        "\u00e1": "a", "\u00e0": "a", "\u00e2": "a",
        "\u00ed": "i", "\u00ec": "i", "\u00ee": "i",
        "\u00f3": "o", "\u00f2": "o", "\u00f4": "o",
        "\u00fa": "u", "\u00f9": "u", "\u00fb": "u",
        "\u00f1": "n", "\u00e7": "c", "\u00df": "ss",
    }
    for k, v in tbl.items():
        s = s.replace(k, v)
    # NFKD-normalize and drop anything latin-1 can't do
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("latin-1", "replace").decode("latin-1").replace("?", "?")
    return s


def slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:60]


# ---------- PDF builder ----------

class StudyPDF(FPDF):
    def __init__(self, title: str, subtitle: str):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.title_str = ascii_safe(title)
        self.subtitle_str = ascii_safe(subtitle)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=16, top=16, right=16)
        self.set_title(f"{title} - {subtitle}")
        self.set_author("NSB MS Study Tool")

    def header(self):
        # No header on cover page (page 1) to keep it clean
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 9)
        self.set_text_color(130)
        self.cell(0, 6, f"{self.title_str}  -  {self.subtitle_str}", align="L")
        self.cell(0, 6, f"Page {self.page_no()}", align="R")
        self.ln(10)
        self.set_text_color(0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130)
        self.cell(0, 6, "NSB Middle School Study Packet | source: science.osti.gov", align="C")
        self.set_text_color(0)

    def cover(self, n_questions: int, gen_date: str):
        self.add_page()
        w = self.epw  # effective page width (page width minus margins)
        self.ln(30)
        self.set_font("Helvetica", "B", 24)
        self.multi_cell(w, 10, "NSB Middle School", new_x="LMARGIN", new_y="NEXT")
        self.multi_cell(w, 10, "Sample Questions Study Packet", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_draw_color(60, 110, 220)
        self.set_line_width(1)
        y = self.get_y()
        self.line(self.l_margin, y, self.l_margin + w, y)
        self.ln(8)
        self.set_font("Helvetica", "", 14)
        self.set_text_color(80)
        self.multi_cell(w, 8, f"Topic: {self.title_str}", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(0)
        self.multi_cell(w, 10, f"{self.subtitle_str}", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(80)
        self.cell(w, 7, f"{n_questions} questions", new_x="LMARGIN", new_y="NEXT")
        self.cell(w, 7, f"Generated {gen_date}", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "I", 11)
        self.multi_cell(
            w,
            6,
            "This packet pairs each toss-up question with the matching bonus "
            "exactly as they appeared in the original NSB round. "
            "The answer key is at the end.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(0)

    def section_title(self, text: str):
        self.add_page()
        self.set_font("Helvetica", "B", 20)
        self.set_fill_color(30, 90, 200)
        self.set_text_color(255)
        self.cell(self.epw, 12, " " + ascii_safe(text), new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(0)
        self.ln(4)

    def round_header(self, label: str):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(230, 236, 246)
        self.cell(self.epw, 7, " " + ascii_safe(label), new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def question(self, number: int, r: dict, show_answer: bool = False):
        """Render one question. If show_answer, print only the answer (for key)."""
        kind = r["kind"]
        fmt = r["format"]
        w = self.epw
        if not show_answer:
            self.set_font("Helvetica", "B", 11)
            tag = f"{number}. {kind}   ({fmt})"
            self.multi_cell(w, 6, ascii_safe(tag), new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 11)

            if fmt == "Multiple Choice":
                stem, choices = parse_mc(r["question"])
                self.multi_cell(w, 5.5, ascii_safe(stem), new_x="LMARGIN", new_y="NEXT")
                self.ln(1)
                for letter, text in choices:
                    self.set_x(self.l_margin + 6)
                    self.multi_cell(w - 6, 5.5, ascii_safe(f"{letter}) {text}"), new_x="LMARGIN", new_y="NEXT")
            else:
                self.multi_cell(w, 5.5, ascii_safe(r["question"]), new_x="LMARGIN", new_y="NEXT")
                self.ln(2)
                self.set_draw_color(180)
                for _ in range(2):
                    y = self.get_y() + 3
                    self.line(self.l_margin + 4, y, self.l_margin + w, y)
                    self.ln(6)
            self.ln(3)
            self.set_draw_color(220)
            self.line(self.l_margin, self.get_y(), self.l_margin + w, self.get_y())
            self.ln(2)
        else:
            self.set_font("Helvetica", "B", 10)
            self.cell(14, 6, f"{number}.")
            self.set_font("Helvetica", "", 10)
            self.multi_cell(w - 14, 6, ascii_safe(f"[{kind}] {r['answer']}"), new_x="LMARGIN", new_y="NEXT")
            self.ln(0.5)


# ---------- main ----------

def main():
    rows = [json.loads(l) for l in DATA.open()]

    # Group by (topic, subtopic)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        topic = r.get("topic6", r.get("topic"))
        if topic not in TARGET_TOPICS:
            continue
        subtopic = r.get("subtopic") or "Other"
        groups[(topic, subtopic)].append(r)

    # Order subtopics by size (biggest first) within each topic
    all_keys = sorted(groups.keys(), key=lambda k: (k[0], -len(groups[k])))

    today = date.today().strftime("%B %d, %Y")
    made = []
    for i, (topic, subtopic) in enumerate(all_keys, 1):
        qs = groups[(topic, subtopic)]
        # Natural order: by source, then number, then TOSS-UP before BONUS
        qs.sort(key=lambda r: (r["source"], r["number"], 0 if r["kind"] == "TOSS-UP" else 1))

        topic_dir = OUT / topic
        topic_dir.mkdir(exist_ok=True)
        # Compute index number within topic
        subs_in_topic = [k for k in all_keys if k[0] == topic]
        topic_idx = subs_in_topic.index((topic, subtopic)) + 1
        fname = f"{topic_idx:02d}_{slug(subtopic)}.pdf"
        out_path = topic_dir / fname

        pdf = StudyPDF(topic, subtopic)
        pdf.cover(len(qs), today)

        pdf.section_title("Questions")
        prev_source = None
        for n, r in enumerate(qs, 1):
            if r["source"] != prev_source:
                # Pretty source: "MS-Sample-Set-1.pdf" -> "From: MS Sample Set 1"
                src = re.sub(r"\.pdf$", "", r["source"], flags=re.I)
                src = re.sub(r"[-_]+", " ", src).strip()
                pdf.round_header(f"From: {src}")
                prev_source = r["source"]
            pdf.question(n, r, show_answer=False)

        pdf.section_title("Answer Key")
        for n, r in enumerate(qs, 1):
            pdf.question(n, r, show_answer=True)

        pdf.output(str(out_path))
        made.append((topic, subtopic, len(qs), out_path))
        print(f"wrote {out_path.relative_to(ROOT)}  ({len(qs)} Qs)")

    print(f"\nTotal: {len(made)} PDFs")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
