"""WF010 — Workflow Performance Report
Steps: Load logs → success/failure rate → avg time → frequent errors → slow steps → recommendations
Decision: Flag failure rate > 10% or avg time > threshold

Nice touch: by default it analyses the engine's OWN logs (logs/executions.csv),
so every demo run you do feeds this report. A sample log is also provided.
"""
import pandas as pd
from engine.executor import BaseHandler, step, LOG_FILE

FAIL_THRESHOLD = 10      # %
TIME_THRESHOLD_MS = 1500


class PerformanceReport(BaseHandler):
    workflow_id = "WF010"

    @step("Load execution logs")
    def load(self):
        # default: sample logs. inputs source=live → analyse this engine's own logs/executions.csv
        if str(self.inputs.get("source", "")).lower() == "live" and LOG_FILE.exists():
            df = self.use("csv_reader")("executions.csv", path=str(LOG_FILE)); src = "live engine logs"
        else:
            df = self.use("csv_reader")(self.inputs.get("file", "execution_logs.csv")); src = "sample logs"
        self.state["df"] = df
        return f"{len(df)} log rows ({src})"

    @step("Calculate success / failure rate")
    def rates(self):
        df = self.state["df"]
        g = df.groupby("workflow_id").agg(runs=("status", "size"),
                                          failures=("status", lambda s: (s != "success").sum()))
        g["failure_rate_pct"] = (g["failures"] / g["runs"] * 100).round(1)
        self.state["g"] = g
        return f"overall failure rate {g['failures'].sum() / g['runs'].sum() * 100:.1f}%"

    @step("Calculate average execution time")
    def times(self):
        self.use("calculator")
        self.state["g"]["avg_ms"] = self.state["df"].groupby("workflow_id")["duration_ms"].mean().round(0)
        return f"slowest avg = {self.state['g']['avg_ms'].max():.0f} ms"

    @step("Identify frequent errors")
    def errors(self):
        df = self.state["df"]
        errs = df[df["status"] != "success"]["error"].dropna().astype(str)
        errs = errs[errs.str.strip() != ""]
        self.state["top_errors"] = errs.value_counts().head(5).to_dict()
        return f"{len(self.state['top_errors'])} distinct error types"

    @step("Identify slow steps")
    def slow(self):
        df = self.state["df"]
        self.state["slow_steps"] = (df[df["failed_step"].notna() & (df["failed_step"].astype(str) != "")]
                                    ["failed_step"].value_counts().head(5).to_dict())
        g = self.state["g"]
        g["flag"] = (g["failure_rate_pct"] > FAIL_THRESHOLD) | (g["avg_ms"] > TIME_THRESHOLD_MS)
        return f"{int(g['flag'].sum())} workflows flagged"

    @step("Generate recommendations")
    def recommend(self):
        g = self.state["g"].reset_index()
        flagged = g[g["flag"]]
        recs = []
        for _, r in flagged.iterrows():
            if r["failure_rate_pct"] > FAIL_THRESHOLD:
                recs.append(f"{r['workflow_id']}: failure rate {r['failure_rate_pct']}% > {FAIL_THRESHOLD}% — add input validation / retries.")
            if r["avg_ms"] > TIME_THRESHOLD_MS:
                recs.append(f"{r['workflow_id']}: avg {r['avg_ms']:.0f} ms > {TIME_THRESHOLD_MS} ms — cache data reads or batch LLM calls.")
        if not recs:
            recs.append("All workflows are within thresholds. Keep monitoring.")
        self.state["output"] = {
            "metrics_per_workflow": g.sort_values("failure_rate_pct", ascending=False).to_dict("records"),
            "most_failing": g.sort_values("failure_rate_pct", ascending=False).head(3)[["workflow_id", "failure_rate_pct"]].to_dict("records"),
            "frequent_errors": self.state["top_errors"],
            "steps_that_fail_most": self.state["slow_steps"],
            "thresholds": {"failure_rate_pct": FAIL_THRESHOLD, "avg_ms": TIME_THRESHOLD_MS},
            "recommendations": recs,
        }
        return f"{len(recs)} recommendations"
