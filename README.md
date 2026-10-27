# NSB Middle School – Sample Questions Study Tool

A Streamlit app that serves [National Science Bowl](https://science.osti.gov/wdts/nsb/Regional-Competitions/Resources/MS-Sample-Questions) Middle School sample questions, grouped into 6 topics:

- Math
- Physics
- Chemistry
- Life Sciences
- Earth and Space
- Energy

All 11,594 questions across the 16 Sample Question Sets (plus the Sample Rounds Round-Robin / Double-Elimination packets) are included, with the original NSB label preserved as metadata.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

- **Streamlit Community Cloud**: [share.streamlit.io](https://share.streamlit.io) → New app → point at this repo → `app.py`
- **Hugging Face Spaces**: create a Streamlit Space → upload `app.py`, `requirements.txt`, `all_questions_classified.jsonl`

## Features

- 10 questions per page (paired toss-up → bonus, in NSB round order)
- Topic / Question-type / Format filters
- Full-text search across questions and answers
- Answers hidden until "Reveal" is clicked (not shipped unless requested)
- Per-session hourly cap (`NSB_MAX_QS_PER_HOUR`, default 400)
- Session watermark footer and basic Ctrl+P / Ctrl+S / right-click deterrents

## Attribution

All questions are from the U.S. Department of Energy Office of Science's
[National Science Bowl](https://science.osti.gov/wdts/nsb) and are public.
