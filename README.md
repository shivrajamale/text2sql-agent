# Natural-Language Data Analysis Agent (Text-to-SQL)

Ask questions about a database in plain English. An LLM-based agent writes the SQL, checks that it is safe,
runs it, and shows the result as a table, a chart and a short explanation.

**Live demo:** https://text2sql-agent.streamlit.app/  
**Code:** https://github.com/shivrajamale/text2sql-agent

> Minor Project (23CSA391A), Amrita Vishwa Vidyapeetham (AHEAD Online)  
> Author: Shivraj Parmeshwar Amale

## Screenshots
_Add 2-3 screenshots here (for example `docs/screenshot1.png`) and link them with `![demo](docs/screenshot1.png)`._

## Features
- Plain-English questions -> SQLite queries (Text-to-SQL) using an LLM
- **Safety check:** only a single read-only `SELECT` is executed (INSERT / UPDATE / DELETE / DROP are blocked)
- **Self-correction:** if a query fails, the error is sent back to the LLM, which retries (up to 2 times)
- **Optional result verification:** after a query runs, the LLM checks whether the result really answers the question and retries if not (checkbox in the sidebar, off by default)
- Shows the generated SQL, a results table, an automatic bar chart and a plain-English explanation
- Use the built-in sample shop database or **upload your own CSV files**
- 4 prompt strategies to compare: question only, schema, schema + sample rows, schema + sample rows + examples
- Evaluation script with a 44-question test set (easy / medium / hard)

## Architecture
```mermaid
flowchart LR
    U[User question] --> P[Prompt builder<br/>schema + sample rows + hints]
    P --> L[LLM writes SQL]
    L --> S{Safety check<br/>SELECT only?}
    S -- no --> R[Retry with error message]
    S -- yes --> X[Run on SQLite]
    X -- error --> R
    R --> L
    X -- ok --> O[Table + chart + explanation]
```

## Results
Execution accuracy on the 44-question test set (10 easy, 12 medium, 22 hard) on the sample shop database.
Each setting was run once with a small local model through Ollama.

| Setting | Accuracy | Easy | Medium | Hard |
|---|---|---|---|---|
| Question only (no schema) | 22.7% (10/44) | 1/10 | 9/12 | 0/22 |
| Schema | 84.1% (37/44) | 10/10 | 12/12 | 15/22 |
| Schema + sample rows | 86.4% (38/44) | 10/10 | 12/12 | 16/22 |
| Schema + sample rows + examples | 86.4% (38/44) | 10/10 | 12/12 | 16/22 |
| Full system + self-correction | 86.4% (38/44) | 10/10 | 12/12 | 16/22 |

**Main finding:** giving the model the database schema raised accuracy from 22.7% to 84.1%. Sample rows, example hints and
self-correction made little or no difference on this test set (one question is about 2.3 percentage points).

### Second run: Gemini API with result verification
A separate run with the Gemini API (full prompt + self-correction + result verification) answered **35 of 44 questions
correctly (79.5%)**: easy 9/10, medium 11/12, hard 15/22. This used a different LLM from the table above, so the two
runs are not directly comparable.

All 9 wrong answers ran without any database error:

| Error type | Count | Example |
|---|---|---|
| Wrong grouping level (extra GROUP BY columns, too many rows) | 3 | Orders per year grouped by year and month |
| Wrong logic (needs a subquery or set operation) | 3 | Average order value; customers in both 2025 and 2026 |
| Missing filter | 1 | Furniture product count returned every category |
| Missing DISTINCT | 1 | Customers from Mumbai who bought a Phone |
| Output format difference | 1 | Month returned as 2026-01 instead of 01 (arguably correct) |

Because these queries did not raise errors, error-based self-correction cannot catch them; this is why the optional
result-verification step was added.

## Setup
```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
set ANTHROPIC_API_KEY=your_key   # Windows  (Mac/Linux: export ANTHROPIC_API_KEY=your_key)
streamlit run app.py
```
Without an API key you can still explore the data with the "Run SQL manually" box.

## Free hosted option: Gemini API (works online too)
1. Get a free key from Google AI Studio (aistudio.google.com) and set `GEMINI_API_KEY`
   (Windows: `set GEMINI_API_KEY=your_key`).
2. Choose **Gemini API** in the sidebar. If the model name stops working, set `GEMINI_MODEL` to a current name from AI Studio.
3. The app waits and retries when the free-tier limit is hit (`GEMINI_MIN_INTERVAL` sets the gap between calls, default 4 seconds).
4. Free-tier limits and data-use terms change: do not send private data, and check the limits in AI Studio.

## Free option: local model with Ollama (no API key, no cost)
1. Install Ollama from https://ollama.com and keep it running.
2. In a terminal run: `ollama pull qwen2.5-coder:3b` (about 2 GB; use `qwen2.5-coder:7b` if you have 16 GB RAM).
3. Run `streamlit run app.py` and choose **Free local model (Ollama)** in the sidebar.
Small local models are slower and less accurate than Claude; comparing both is a good point for the report.
(Ollama works only on your own computer, not on Streamlit Cloud.)

## Run the evaluation
```bash
python eval.py verify  # only the setting with result verification (all questions)
python eval.py quick   # fast: 12 questions x 2 settings
python eval.py         # full: all questions x 5 settings (slow with a local model)
```
Results of every question are saved in `eval_details.csv` (`eval_details_verify.csv` for the verify run).
If the LLM returns errors (for example the Gemini free-tier limit), the run reports them as ERROR, stops after 5 in a row,
and marks the summary NOT VALID; those numbers must not be used.

## Project structure
| File | Purpose |
|---|---|
| `app.py` | Streamlit web interface |
| `agent.py` | Database loading, prompts, safety check, LLM calls, agent loop with self-correction |
| `test_set.py` | Test questions with correct SQL |
| `eval.py` | Execution-accuracy evaluation for different settings |

## Deployment (Streamlit Community Cloud)
1. Push this folder to a GitHub repository (do **not** upload your API key).
2. On share.streamlit.io choose **New app**, select the repo, and set the main file to `app.py`.
3. Under **Advanced settings -> Secrets** add `GEMINI_API_KEY` (see `secrets.toml.example`).
4. In the deployed app choose **Gemini API** in the sidebar (Ollama works only on your own computer).

## Limitations
- Works on SQLite only; very large or very complex schemas may reduce accuracy.
- The LLM can still write wrong SQL; always check the generated query.
- Uploaded CSV data lives only in memory for the current session.

## Future work
- Support more databases (MySQL / PostgreSQL), multilingual questions (Hindi), conversation memory for follow-up questions, and more chart types.