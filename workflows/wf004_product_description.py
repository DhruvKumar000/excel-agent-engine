"""WF004 — Product Description Generator
Steps: Validate attributes → description → short description → SEO title → meta description
Decision: Do not invent missing attributes; explicitly mark missing information
"""
from engine.executor import BaseHandler, step
from engine.models import NeedsInput

ATTRS = ["product_name", "category", "attributes", "material", "color", "target_audience"]


class ProductDescription(BaseHandler):
    workflow_id = "WF004"

    @step("Validate required attributes")
    def validate(self):
        present = {k: v for k, v in self.inputs.items() if k in ATTRS and str(v).strip()}
        missing = [k for k in ATTRS if k not in present]
        if "product_name" not in present:
            raise NeedsInput("Product name is required. Please provide at least 'product_name' "
                             "(optionally category, attributes, material, color, target_audience).")
        self.state["present"], self.state["missing"] = present, missing
        return f"present: {list(present)} | missing: {missing}"

    def _ask(self, what, limit):
        facts = "\n".join(f"- {k}: {v}" for k, v in self.state["present"].items())
        prompt = (f"Write a {what} ({limit}) for this product using ONLY these facts:\n{facts}\n"
                  f"Attributes NOT provided: {', '.join(self.state['missing']) or 'none'}. "
                  "Do NOT invent them. If relevant, write '[missing: attribute]'. Reply with the text only.")
        return self.use("llm")(prompt)

    @step("Create product description")
    def long_desc(self):
        self.state["description"] = self._ask("product description", "60-90 words")
        return self.state["description"][:80]

    @step("Generate short description")
    def short_desc(self):
        self.state["short"] = self._ask("short description", "max 20 words")
        return self.state["short"][:80]

    @step("Generate SEO title")
    def seo_title(self):
        self.state["seo_title"] = self._ask("SEO title", "max 60 characters")
        return self.state["seo_title"][:80]

    @step("Generate meta description")
    def meta(self):
        self.state["meta"] = self._ask("meta description", "max 155 characters")
        self.state["output"] = {
            "product_description": self.state["description"],
            "short_description": self.state["short"],
            "seo_title": self.state["seo_title"],
            "meta_description": self.state["meta"],
            "missing_attributes_flagged": self.state["missing"],
        }
        return "content package ready"
