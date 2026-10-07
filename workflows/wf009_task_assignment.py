"""WF009 — Employee Task Assignment
Steps: Understand task → compare skills → check workload → rank → select → summary
Decision: Prefer required skills + available capacity; escalate if nobody suitable
"""
import re
from engine.executor import BaseHandler, step
from engine.models import NeedsInput

SKILL_WORDS = ["python", "react", "sql", "aws", "django", "node", "ui", "testing", "devops", "ml"]
MAX_WORKLOAD = 80  # % capacity


class TaskAssignment(BaseHandler):
    workflow_id = "WF009"

    @step("Understand task requirements")
    def understand(self):
        desc = str(self.inputs.get("task_description") or self.request)
        skills = self.inputs.get("skills") or [w for w in SKILL_WORDS if w in desc.lower()]
        if isinstance(skills, str):
            skills = [s.strip().lower() for s in skills.split(",")]
        if not skills:
            raise NeedsInput("Which skills does this task need? e.g. skills='python, sql'")
        urgent = "urgent" in desc.lower() or str(self.inputs.get("priority", "")).lower() == "high"
        self.state.update(desc=desc, skills=[s.lower() for s in skills], priority="high" if urgent else "normal",
                          deadline=self.inputs.get("deadline", "ASAP" if urgent else "not specified"))
        return f"skills={self.state['skills']} priority={self.state['priority']}"

    @step("Compare employee skills")
    def skills(self):
        df = self.use("csv_reader")(self.inputs.get("employees_file", "employees.csv"))
        df["skill_set"] = df["skills"].str.lower().str.split(";").apply(lambda l: {s.strip() for s in l})
        df["skill_match"] = df["skill_set"].apply(lambda s: len(set(self.state["skills"]) & s) / len(self.state["skills"]))
        self.state["df"] = df
        return f"{(df['skill_match'] == 1).sum()} employees have all skills"

    @step("Check current workload")
    def workload(self):
        df = self.state["df"]
        df["available"] = df["workload_pct"] < MAX_WORKLOAD
        return f"{df['available'].sum()} employees under {MAX_WORKLOAD}% load"

    @step("Rank candidates")
    def rank(self):
        df = self.state["df"]
        df["score"] = (df["skill_match"] * 70 + (100 - df["workload_pct"]) * 0.3).round(1)
        self.state["ranked"] = df[df["skill_match"] > 0].sort_values("score", ascending=False)
        return " > ".join(self.state["ranked"]["name"].head(3))

    @step("Select employee")
    def select(self):
        ok = self.state["ranked"][self.state["ranked"]["available"] & (self.state["ranked"]["skill_match"] >= 0.5)]
        if ok.empty:
            self.state["escalate"] = True
            return "ESCALATE — no suitable employee with capacity"
        self.state["chosen"] = ok.iloc[0]
        return f"selected {self.state['chosen']['name']}"

    @step("Generate assignment summary")
    def summary(self):
        if self.state.get("escalate"):
            self.state["output"] = {"recommended_employee": None, "escalation": True,
                                    "reasoning": "No employee has the required skills with available capacity. Escalate to manager.",
                                    "priority": self.state["priority"], "deadline": self.state["deadline"],
                                    "task_summary": self.state["desc"],
                                    "candidates_considered": self.state["ranked"][["name", "skill_match", "workload_pct", "score"]].to_dict("records")}
            return "escalation summary generated"
        c = self.state["chosen"]
        self.state["output"] = {
            "recommended_employee": c["name"], "role": c["role"],
            "reasoning": f"{c['name']} matches {int(c['skill_match']*100)}% of required skills ({', '.join(self.state['skills'])}) "
                         f"and is at {c['workload_pct']}% workload (< {MAX_WORKLOAD}%).",
            "priority": self.state["priority"], "deadline": self.state["deadline"],
            "task_summary": self.state["desc"],
            "runner_ups": self.state["ranked"][["name", "skill_match", "workload_pct", "score"]].iloc[1:3].to_dict("records"),
        }
        return f"assigned to {c['name']}"
