"""Execution-accuracy evaluation of the agent on the SAMPLE shop database.
Compares prompt strategies and self-correction on/off.
Questions live in test_set.py (add your own there, aim for 40-50 in total).
Run:  python eval.py heldout  (12 NEW questions: old prompt vs v2 prompt; the fair test)\n      python eval.py v2       (v2 prompt on the 44 questions; optimistic, see README)\n      python eval.py verify  (only the "verify" setting, all questions; keeps old results)\n      python eval.py quick   (fast: 12 questions x 2 settings)\n      python eval.py         (full: 32 questions x 5 settings; slow with a local model)\nUses the LLM chosen in agent.py (Ollama if no ANTHROPIC_API_KEY is set)."""
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
    only_verify = "verify" in sys.argv  # python eval.py verify -> only the new "verify" setting (44 questions)
    configs = CONFIGS[-1:] if only_verify else ([CONFIGS[0], CONFIGS[3]] if quick else CONFIGS)
    out_file = "eval_details_verify.csv" if only_verify else "eval_details.csv"  # so the old results are not overwritten
    tests = TESTS
    if "heldout" in sys.argv:  # NEW unseen questions: compares the old prompt with the v2 prompt (no verify)
        from test_set_heldout import TESTS_HELDOUT
        configs = [("schema_samples_fewshot", 2), ("schema_samples_fewshot_v2", 2)]
        out_file, tests = "eval_details_heldout.csv", TESTS_HELDOUT
    elif "v2" in sys.argv:  # the v2 prompt on the original 44 questions (v2 was designed after seeing these errors)
        configs = [("schema_samples_fewshot_v2", 2)]
        out_file = "eval_details_v2.csv"
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
        correct, by_level, errors, streak, aborted = 0, {}, 0, 0, False
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
            status = "PASS" if ok else ("ERROR" if sql.startswith("ERROR:") else "FAIL")  # ERROR = LLM/network problem, not a wrong answer
            errors += status == "ERROR"
            streak = streak + 1 if status == "ERROR" else 0
            details.append([name, level, q, status, sql.replace("\n", " ")])
            print(f"[{name}] {i}/{len(tests)} {status} | {q}" + (f"  -> {sql[:110]}" if status == "ERROR" else ""), flush=True)
            with open(out_file, "w", newline="", encoding="utf-8") as f:  # saved after every question
                w = csv.writer(f); w.writerow(["setting", "level", "question", "result", "generated_sql"]); w.writerows(details)
            if streak >= 5:  # 5 LLM errors in a row: stop, the numbers would be meaningless
                aborted = True
                print("\n!! STOPPED: 5 LLM errors in a row (see the message above). Fix the problem "
                      "(internet, API limit, Ollama not running) and run again.\n")
                break
        levels = ", ".join(f"{l}: {c}/{n}" for l, (n, c) in by_level.items())
        flag = "   <-- NOT VALID: stopped early" if aborted else (f"   <-- NOT VALID: {errors} LLM errors" if errors else "")
        summary.append(f"{name:45s} {100 * correct / len(tests):5.1f}%   ({levels}){flag}")

    print("\n===== SUMMARY (copy into your report) =====")
    print("\n".join(summary))
    if any("NOT VALID" in line for line in summary):
        print("\nWARNING: some questions got LLM errors instead of answers. Those are NOT wrong answers; "
              "do not use these numbers in the report. Fix the cause and re-run.")
    print(f"\nTime taken: {(time.time() - start) / 60:.1f} min. Every question's result is saved in {out_file}")
