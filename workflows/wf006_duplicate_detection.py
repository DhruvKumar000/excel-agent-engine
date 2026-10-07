"""WF006 — Duplicate Product Detection
Steps: Load products → normalize names/SKUs → compare identifiers → compare attributes → group → confidence
Decision: Exact SKU match = definite duplicate; high attribute similarity = possible duplicate
"""
import re
from itertools import combinations
from engine.executor import BaseHandler, step

SIM_THRESHOLD = 0.85


class DuplicateDetection(BaseHandler):
    workflow_id = "WF006"

    @step("Load products")
    def load(self):
        self.state["df"] = self.use("csv_reader")(self.inputs.get("file", "catalog.csv"))
        return f"{len(self.state['df'])} products"

    @step("Normalize names and SKUs")
    def normalize(self):
        df = self.state["df"]
        df["sku_norm"] = df["sku"].astype(str).str.upper().str.replace(r"[\s\-_]", "", regex=True)
        df["name_norm"] = df["product_name"].astype(str).str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True).str.strip()
        return "sku upper/no-dashes, name lower/no-punctuation"

    @step("Compare identifiers (exact SKU)")
    def compare_sku(self):
        df = self.state["df"]
        groups = []
        for sku, g in df.groupby("sku_norm"):
            if len(g) > 1:
                groups.append({"type": "definite", "confidence": 1.0, "matched_on": "sku",
                               "products": g[["sku", "product_name", "category"]].to_dict("records")})
        self.state["groups"] = groups
        return f"{len(groups)} exact-SKU groups"

    @step("Compare product attributes (similarity)")
    def compare_attrs(self):
        sim = self.use("text_similarity")
        df = self.state["df"]
        seen = {tuple(sorted(p["sku"] for p in g["products"])) for g in self.state["groups"]}
        possible = []
        for (i, a), (j, b) in combinations(df.iterrows(), 2):
            if a["sku_norm"] == b["sku_norm"]:
                continue
            score = sim(a["name_norm"], b["name_norm"])
            if score >= SIM_THRESHOLD and a["category"] == b["category"]:
                key = tuple(sorted([a["sku"], b["sku"]]))
                if key not in seen:
                    seen.add(key)
                    possible.append({"type": "possible", "confidence": score, "matched_on": "name+category",
                                     "products": [a[["sku", "product_name", "category"]].to_dict(),
                                                  b[["sku", "product_name", "category"]].to_dict()]})
        self.state["possible"] = possible
        return f"{len(possible)} similar pairs ≥ {SIM_THRESHOLD}"

    @step("Group likely duplicates")
    def group(self):
        self.state["all"] = self.state["groups"] + self.state["possible"]
        return f"{len(self.state['all'])} total groups"

    @step("Assign confidence")
    def confidence(self):
        self.state["output"] = {"duplicate_groups": sorted(self.state["all"], key=lambda g: -g["confidence"]),
                                "definite": len(self.state["groups"]), "possible": len(self.state["possible"])}
        return "definite=1.0, possible=similarity score"
