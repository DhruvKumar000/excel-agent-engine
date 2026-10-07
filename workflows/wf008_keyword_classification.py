"""WF008 — SEO Keyword Classification
Steps: Read keywords → remove duplicates → classify intent → map to categories → high priority → export
Decision: informational | commercial | transactional | navigational
"""
from engine.executor import BaseHandler, step
from engine.tools import DATA_DIR

INTENT_RULES = {
    "transactional": ["buy", "order", "price", "cheap", "discount", "deal", "shop", "sale"],
    "commercial":    ["best", "top", "review", "vs", "compare", "comparison"],
    "navigational":  ["login", "website", "official", "near me", "store", "app"],
}
PAGE_FOR_INTENT = {"transactional": "product page", "commercial": "category / comparison page",
                   "navigational": "home / store page", "informational": "blog article"}


class KeywordClassification(BaseHandler):
    workflow_id = "WF008"

    @step("Read keywords")
    def read(self):
        self.state["df"] = self.use("csv_reader")(self.inputs.get("file", "keywords.csv"))
        prods = self.use("csv_reader")("products.csv")
        # product word → category  (e.g. "shoes" → footwear, "wallet" → accessories)
        self.state["word2cat"] = {w.lower().rstrip("s"): c.lower()
                                  for name, c in zip(prods["product_name"], prods["category"])
                                  for w in name.split() if len(w) > 3 and w.lower() not in ("white", "blue", "brown", "black", "grey", "pack", "cotton", "wool", "denim", "leather", "canvas", "sports")}
        self.state["cats"] = prods["category"].str.lower().unique().tolist()
        return f"{len(self.state['df'])} keywords, {len(self.state['cats'])} categories"

    @step("Remove duplicates")
    def dedupe(self):
        df = self.state["df"]
        df["keyword"] = df["keyword"].str.lower().str.strip()
        before = len(df)
        self.state["df"] = df.drop_duplicates("keyword").reset_index(drop=True)
        return f"removed {before - len(self.state['df'])} duplicates"

    @step("Classify search intent")
    def intent(self):
        def classify(kw):
            for intent, words in INTENT_RULES.items():
                if any(w in kw for w in words):
                    return intent
            return "informational"
        self.state["df"]["intent"] = self.state["df"]["keyword"].apply(classify)
        return self.state["df"]["intent"].value_counts().to_dict()

    @step("Map keywords to categories")
    def map_cat(self):
        cats, w2c = self.state["cats"], self.state["word2cat"]
        def to_cat(kw):
            for c in cats:                       # category named directly
                if c.rstrip("s") in kw:
                    return c
            for w, c in w2c.items():             # product word in keyword
                if w in kw:
                    return c
            return "general"
        self.state["df"]["category"] = self.state["df"]["keyword"].apply(to_cat)
        return self.state["df"]["category"].value_counts().to_dict()

    @step("Identify high-priority keywords")
    def priority(self):
        df = self.state["df"]
        def prio(r):
            score = r["monthly_volume"] * {"transactional": 1.5, "commercial": 1.2}.get(r["intent"], 1.0)
            return "high" if score >= 3000 else "medium" if score >= 1000 else "low"
        df["priority"] = df.apply(prio, axis=1)
        df["recommended_page"] = df["intent"].map(PAGE_FOR_INTENT)
        return f"{(df['priority'] == 'high').sum()} high-priority"

    @step("Export results")
    def export(self):
        out = DATA_DIR.parent.parent / "examples" / "outputs" / "keyword_report.csv"
        self.state["df"].to_csv(out, index=False)
        self.state["output"] = {"report_file": str(out.relative_to(DATA_DIR.parent.parent)),
                                "keywords": self.state["df"].to_dict("records")}
        return f"saved → {out.name}"
