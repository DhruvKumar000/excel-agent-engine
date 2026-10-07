"""WF007 — Marketing Campaign Brief
Steps: Validate inputs → objective → summarize products → messaging → channels → checklist
Decision: If campaign goal or dates are missing, request them before generating
"""
from engine.executor import BaseHandler, step
from engine.models import NeedsInput


class CampaignBrief(BaseHandler):
    workflow_id = "WF007"

    @step("Validate inputs")
    def validate(self):
        missing = [k for k in ("campaign_goal", "dates") if not str(self.inputs.get(k, "")).strip()]
        if missing:
            raise NeedsInput(f"Before I create the brief I need: {', '.join(missing)}. "
                             "Example: campaign_goal='Launch summer collection', dates='1–15 June'.")
        return "goal and dates present"

    @step("Identify campaign objective")
    def objective(self):
        goal = self.inputs["campaign_goal"].lower()
        kind = ("awareness" if any(w in goal for w in ("launch", "awareness", "new")) else
                "conversion" if any(w in goal for w in ("sale", "sell", "revenue", "discount")) else "engagement")
        self.state["objective"] = kind
        return f"objective type = {kind}"

    @step("Summarize products")
    def products(self):
        plist = self.inputs.get("product_list") or []
        if isinstance(plist, str):
            plist = [p.strip() for p in plist.split(",") if p.strip()]
        if not plist:  # fall back to catalog
            df = self.use("csv_reader")("products.csv")
            plist = df["product_name"].head(5).tolist()
        self.state["products"] = plist
        return f"{len(plist)} products: {', '.join(plist[:3])}..."

    @step("Create messaging")
    def messaging(self):
        prompt = (f"Write a campaign brief messaging block (headline + 2 key messages + tone) for:\n"
                  f"Goal: {self.inputs['campaign_goal']}\nObjective type: {self.state['objective']}\n"
                  f"Audience: {self.inputs.get('target_audience', 'general shoppers')}\n"
                  f"Promotion: {self.inputs.get('promotion', 'none')}\nProducts: {', '.join(self.state['products'])}")
        self.state["messaging"] = self.use("llm")(prompt)
        return self.state["messaging"][:80]

    @step("Create channel recommendations")
    def channels(self):
        aud = str(self.inputs.get("target_audience", "")).lower()
        ch = ["Instagram", "Email"] + (["TikTok"] if "young" in aud or "gen z" in aud else ["Google Ads"])
        if self.state["objective"] == "conversion":
            ch.append("Retargeting")
        self.state["channels"] = ch
        return ", ".join(ch)

    @step("Create campaign checklist")
    def checklist(self):
        self.state["output"] = {
            "objective": f"{self.state['objective'].title()} — {self.inputs['campaign_goal']}",
            "audience": self.inputs.get("target_audience", "general shoppers"),
            "products": self.state["products"],
            "promotion": self.inputs.get("promotion", "none"),
            "messaging": self.state["messaging"],
            "channels": self.state["channels"],
            "timeline": self.inputs["dates"],
            "checklist": ["Finalise creatives", "Build landing page", "Set up tracking/UTMs",
                          "Schedule posts & emails", "Launch", "Mid-campaign review", "Post-campaign report"],
        }
        return "7-item checklist created"
