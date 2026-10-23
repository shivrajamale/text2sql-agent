"""Execution-accuracy evaluation of the agent on the SAMPLE shop database.
Compares prompt strategies and self-correction on/off.
Questions live in test_set.py (add your own there, aim for 40-50 in total).
Run:  python eval.py quick   (fast: 12 questions x 2 settings)\n      python eval.py         (full: 32 questions x 5 settings; slow with a local model)\nUses the LLM chosen in agent.py (Ollama if no ANTHROPIC_API_KEY is set)."""
import sqlite3
import agent

from test_set import TESTS

CONFIGS = [  # (strategy, max_retries)
    ("no_schema", 0),
    ("schema", 0),
    ("schema_samples", 0),
    ("schema_samples_fewshot", 0),
    ("schema_samples_fewshot", 2),  # full system: with self-correction
    ("schema_samples_fewshot", 2, True),  # + result verification (LLM checks the result)
]


def same_result(gen, gold):
    """Correct if: same number of rows, and every column of the gold result also appears
    (same values, any order) among the generated columns. Extra columns are allowed."""
    if len(gen) != len(gold):
        return False
    col = lambda df, i: sorted((round(x, 2) if isinstance(x, float) else x for x in df.iloc[:, i].tolist()), key=str)
    gen_cols = [col(gen, i) for i in range(gen.shape[1])]
    return all(col(gold, j) in gen_cols for j in range(gold.shape[1]))


if __name__ == "__main__":
    import sys, time, csv
    quick = "quick" in sys.argv  # python eval.py quick  -> small, fast run
    configs = [CONFIGS[0], CONFIGS[3]] if quick else CONFIGS
    tests = TESTS
    if quick:  # first 4 questions of each difficulty level
        tests, seen = [], {}
        for t in TESTS:
            if seen.get(t[2], 0) < 4:
                tests.append(t); seen[t[2]] = seen.get(t[2], 0) + 1
    print(f"LLM: {agent.PROVIDER} | {len(tests)} questions x {len(configs)} settings"
          f" = {len(tests) * len(configs)} LLM runs. A local model may need 10-60 s each.\n")

    conn = sqlite3.connect(agent.seed_sample_db("sample.db"))
    details, summary = [], []
    start = time.time()
    for cfg in configs:
        strategy, retries = cfg[0], cfg[1]
        verify = len(cfg) > 2 and cfg[2]
        correct, by_level = 0, {}
        name = f"{strategy} | retries={retries}" + (" | verify" if verify else "")
        for i, (q, gold, level) in enumerate(tests, 1):
            sql, ok = "", False
            try:
                res = agent.answer_question(conn, q, max_retries=retries, strategy=strategy, verify=verify)
                sql = res["sql"] or ""
                ok = res["df"] is not None and same_result(res["df"], agent.run_query(conn, gold))
            except Exception as e:
                sql = f"ERROR: {e}"
            correct += ok
            n, c = by_level.get(level, (0, 0))
            by_level[level] = (n + 1, c + ok)
            details.append([name, level, q, "PASS" if ok else "FAIL", sql.replace("\n", " ")])
            print(f"[{name}] {i}/{len(tests)} {'PASS' if ok else 'FAIL'} | {q}", flush=True)
            with open("eval_details.csv", "w", newline="", encoding="utf-8") as f:  # saved after every question
                w = csv.writer(f); w.writerow(["setting", "level", "question", "result", "generated_sql"]); w.writerows(details)
        levels = ", ".join(f"{l}: {c}/{n}" for l, (n, c) in by_level.items())
        summary.append(f"{name:45s} {100 * correct / len(tests):5.1f}%   ({levels})")

    print("\n===== SUMMARY (copy into your report) =====")
    print("\n".join(summary))
    print(f"\nTime taken: {(time.time() - start) / 60:.1f} min. Every question's result is saved in eval_details.csv")