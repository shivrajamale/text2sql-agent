"""Core logic of the Natural-Language Data Analysis Agent (no UI code here)."""
import os
import re
import json
import urllib.request
import urllib.error
import random
import sqlite3
import pandas as pd

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|truncate|vacuum)\b", re.I
)


# ---------------- Sample database ----------------
def seed_sample_db(path="sample.db"):
    """Create a small shop database (customers, products, orders, order_items) if it doesn't exist."""
    if os.path.exists(path):
        return path
    random.seed(42)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
    CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
    CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT);
    CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER);
    """)
    cities = ["Mumbai", "Pune", "Delhi", "Bengaluru", "Chennai", "Kolkata"]
    c.executemany("INSERT INTO customers VALUES(?,?,?)",
                  [(i, f"Customer {i}", random.choice(cities)) for i in range(1, 31)])
    products = [("Laptop", "Electronics", 55000), ("Phone", "Electronics", 25000),
                ("Headphones", "Electronics", 2500), ("Desk", "Furniture", 8000),
                ("Chair", "Furniture", 5000), ("Notebook", "Stationery", 60),
                ("Pen", "Stationery", 10), ("Backpack", "Accessories", 1500),
                ("Water Bottle", "Accessories", 400), ("Monitor", "Electronics", 12000),
                ("Keyboard", "Electronics", 1500), ("Lamp", "Furniture", 1200)]
    c.executemany("INSERT INTO products VALUES(?,?,?,?)",
                  [(i + 1, n, cat, p) for i, (n, cat, p) in enumerate(products)])
    item_id = 1
    for oid in range(1, 201):
        date = f"{random.choice([2025, 2026])}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        c.execute("INSERT INTO orders VALUES(?,?,?)", (oid, random.randint(1, 30), date))
        for pid in random.sample(range(1, 13), random.randint(1, 3)):
            c.execute("INSERT INTO order_items VALUES(?,?,?,?)", (item_id, oid, pid, random.randint(1, 4)))
            item_id += 1
    conn.commit()
    conn.close()
    return path


def get_schema(conn):
    rows = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    return "\n".join(r[0] for r in rows if r[0])


# ---------------- Load your own CSV ----------------
def clean_name(name, fallback="col"):
    """Make a safe SQL name: lowercase, letters/digits/underscore only."""
    n = re.sub(r"\W+", "_", str(name)).strip("_").lower() or fallback
    return "t_" + n if n[0].isdigit() else n


def load_csv_to_db(conn, df, table_name):
    """Clean column names, then save a DataFrame as a table in SQLite. Returns the table name."""
    seen, cols = {}, []
    for c in df.columns:
        base = clean_name(c)
        seen[base] = seen.get(base, 0) + 1
        cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    df = df.copy()
    df.columns = cols
    table = clean_name(table_name, "data")
    df.to_sql(table, conn, if_exists="replace", index=False)
    return table


# ---------------- Safety ----------------
def is_safe(sql):
    """Allow only a single read-only SELECT / WITH query. Returns (ok, reason)."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        return False, "Only one SQL statement is allowed."
    if not re.match(r"^(select|with)\b", s, re.I):
        return False, "Only SELECT queries are allowed."
    if FORBIDDEN.search(s):
        return False, "Query contains a forbidden keyword."
    return True, ""


def clean_sql(text):
    text = re.sub(r"```(?:sql)?", "", text, flags=re.I).replace("```", "")
    return text.strip().rstrip(";").strip()


# ---------------- LLM ----------------
# Which LLM to use: "claude" (needs ANTHROPIC_API_KEY) or "ollama" (free, runs on your laptop)
PROVIDER = os.getenv("LLM_PROVIDER") or ("claude" if os.getenv("ANTHROPIC_API_KEY") else
                                         "gemini" if os.getenv("GEMINI_API_KEY") else "ollama")
# Gemini model names change over time: check Google AI Studio and set GEMINI_MODEL if this one stops working.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")


def llm_ready():
    if PROVIDER == "ollama":
        return True
    if PROVIDER == "gemini":
        return bool(os.getenv("GEMINI_API_KEY"))
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _gemini(prompt, system, max_tokens):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": max(max_tokens, 1024)},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json", "x-goog-api-key": os.getenv("GEMINI_API_KEY", "")})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RuntimeError("Gemini free-tier limit reached. Wait a minute and try again.")
        if e.code == 404:
            raise RuntimeError(f"Gemini model '{GEMINI_MODEL}' not found. Look up a current model name in Google AI "
                               "Studio and set it in GEMINI_MODEL.")
        if e.code in (400, 401, 403):
            raise RuntimeError("Gemini rejected the request. Check that GEMINI_API_KEY is correct.")
        raise RuntimeError(f"Gemini error {e.code}")
    except urllib.error.URLError:
        raise RuntimeError("Could not reach the Gemini API. Check your internet connection.")
    except (KeyError, IndexError):
        raise RuntimeError("Gemini returned no answer (the request may have been blocked). Try rephrasing.")


def _ollama(prompt, system, max_tokens):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": max_tokens},
    }
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())["message"]["content"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Model '{OLLAMA_MODEL}' is not downloaded. Run in a terminal: ollama pull {OLLAMA_MODEL}")
        raise RuntimeError(f"Ollama error {e.code}")
    except urllib.error.URLError:
        raise RuntimeError("Could not reach Ollama. Install it from ollama.com, open it (keep it running), "
                           f"and run once in a terminal: ollama pull {OLLAMA_MODEL}")


def llm(prompt, system="", max_tokens=500):
    if PROVIDER == "ollama":
        return _ollama(prompt, system, max_tokens)
    if PROVIDER == "gemini":
        return _gemini(prompt, system, max_tokens)
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.messages.create(
        model=os.getenv("LLM_MODEL", "claude-sonnet-5-5"),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


STRATEGIES = {
    "no_schema": "Question only (baseline)",
    "schema": "Schema",
    "schema_samples": "Schema + sample rows",
    "schema_samples_fewshot": "Schema + sample rows + examples",
}

FEWSHOT = """Hints for writing correct SQLite queries:
- Use only the tables and columns shown above; never invent column names.
- Use GROUP BY with COUNT/SUM/AVG for "how many / total / average per ..." questions.
- Use ORDER BY ... DESC LIMIT n for "top n / most / highest" questions.
- Join tables on their id columns (for example orders.customer_id = customers.id).
- For dates stored as text 'YYYY-MM-DD', use strftime('%Y', col) for the year and strftime('%m', col) for the month.
- Give calculated columns a short alias with AS.

Examples (different table names, same patterns):
Q: How many rows are in table a?
SQL: SELECT COUNT(*) AS total FROM a
Q: Which group_col has the highest total of value_col?
SQL: SELECT group_col, SUM(value_col) AS total FROM a GROUP BY group_col ORDER BY total DESC LIMIT 1
Q: Show the name from table b for every row in table a (a.b_id refers to b.id).
SQL: SELECT b.name, COUNT(*) AS n FROM a JOIN b ON a.b_id = b.id GROUP BY b.name"""


def sample_rows(conn, n=3):
    """First n rows of every table, as short text (helps the LLM see real values)."""
    out = []
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        cur = conn.execute(f'SELECT * FROM "{t}" LIMIT {n}')
        cols = [d[0] for d in cur.description]
        rows = "\n".join("  " + str(r) for r in cur.fetchall())
        out.append(f"Sample rows from {t} ({', '.join(cols)}):\n{rows}")
    return "\n".join(out)


def build_context(conn, strategy="schema_samples_fewshot"):
    """Build the database information that goes into the prompt, depending on the strategy."""
    if strategy == "no_schema":
        return ""
    ctx = "Database schema:\n" + get_schema(conn)
    if strategy in ("schema_samples", "schema_samples_fewshot"):
        ctx += "\n\n" + sample_rows(conn)
    if strategy == "schema_samples_fewshot":
        ctx += "\n\n" + FEWSHOT
    return ctx


def generate_sql(question, context, prev_sql=None, error=None):
    system = ("You are an expert SQLite analyst. Reply with ONE SQLite SELECT query only, "
              "no explanation, no markdown.")
    prompt = (context + "\n\n" if context else "") + f"Question: {question}\n"
    if prev_sql and error:
        prompt += f"\nYour previous query:\n{prev_sql}\nfailed with error:\n{error}\nWrite a corrected query."
    return clean_sql(llm(prompt, system))


def explain(question, sql, df):
    preview = df.head(15).to_string(index=False)
    prompt = (f"Question: {question}\nSQL used: {sql}\nResult (first rows):\n{preview}\n\n"
              "Explain the answer in 2-3 simple sentences for a non-technical person.")
    return llm(prompt, max_tokens=250)


# ---------------- Agent loop ----------------
def run_query(conn, sql):
    return pd.read_sql_query(sql, conn)


def verify_result(question, sql, df):
    """Ask the LLM whether the result really answers the question. Returns (ok, reason)."""
    preview = df.head(10).to_string(index=False) if len(df) else "(no rows)"
    prompt = (f"Question: {question}\nSQL used: {sql}\nResult ({len(df)} rows, first rows shown):\n{preview}\n\n"
              "Does this result correctly answer the question? Check that the right columns, filters, joins and "
              "grouping were used. Reply with exactly OK if it is correct. Otherwise reply WRONG: followed by "
              "one short sentence explaining what is wrong.")
    text = llm(prompt, "You are a careful SQL reviewer.", 120).strip()
    return text.upper().startswith("OK"), text


def answer_question(conn, question, max_retries=2, strategy="schema_samples_fewshot", verify=False):
    """Generate SQL -> validate -> run -> on error, feed error back and retry.
    max_retries=0 turns self-correction off. strategy chooses how much info the prompt contains.
    verify=True also checks, after a query runs, that the result answers the question (uses a retry if it does not)."""
    context = build_context(conn, strategy)
    sql, error, attempts, fallback = None, None, 0, None
    for _ in range(max_retries + 1):
        attempts += 1
        sql = generate_sql(question, context, prev_sql=sql, error=error)
        ok, reason = is_safe(sql)
        if not ok:
            error = reason
            continue
        try:
            df = run_query(conn, sql)
        except Exception as e:  # SQL error -> retry with the error message
            error = str(e)
            continue
        result = {"sql": sql, "df": df, "error": None, "attempts": attempts}
        if verify and attempts <= max_retries:  # only check if a retry is still available
            good, why = verify_result(question, sql, df)
            if not good:
                fallback = fallback or result  # keep the first working result in case later attempts fail
                error = f"The query ran but the result does not answer the question. {why}"
                continue
        return result
    return fallback or {"sql": sql, "df": None, "error": error, "attempts": attempts}