"""WF002 — Product Price Validation
Steps: Load prices → match by SKU → compare internal vs vendor → % difference → flag exceptions
Decision: Flag when price difference exceeds 10%
"""
from engine.executor import BaseHandler, step

THRESHOLD_PCT = 10


class PriceValidation(BaseHandler):
    workflow_id = "WF002"

    @step("Load product prices")
    def load(self):
        read = self.use("csv_reader")
        self.state["products"] = read(self.inputs.get("products_file", "products.csv"))
        self.state["vendor"] = read(self.inputs.get("vendor_file", "vendor_prices.csv"))
        return f"{len(self.state['products'])} products, {len(self.state['vendor'])} vendor prices"

    @step("Match products by SKU")
    def match(self):
        merged = self.state["products"].merge(self.state["vendor"], on="sku", how="inner",
                                              suffixes=("_internal", "_vendor"))
        self.state["merged"] = merged
        unmatched = len(self.state["products"]) - len(merged)
        return f"{len(merged)} matched, {unmatched} unmatched"

    @step("Compare internal and vendor prices")
    def compare(self):
        m = self.state["merged"]
        m["diff_abs"] = (m["vendor_price"] - m["price"]).round(2)
        return "absolute differences computed"

    @step("Calculate percentage difference")
    def pct(self):
        pd_tool = self.use("calculator")
        m = self.state["merged"]
        m["diff_pct"] = [pd_tool(a, b) for a, b in zip(m["price"], m["vendor_price"])]
        return "percentage differences computed"

    @step("Flag exceptions (> 10%)")
    def flag(self):
        m = self.state["merged"]
        m["exception"] = m["diff_pct"].abs() > THRESHOLD_PCT
        exc = m[m["exception"]]
        self.state["output"] = {
            "threshold_pct": THRESHOLD_PCT,
            "matched_products": len(m),
            "exceptions": exc[["sku", "product_name", "price", "vendor_price", "diff_pct"]].to_dict("records"),
            "all_comparisons": m[["sku", "price", "vendor_price", "diff_pct", "exception"]].to_dict("records"),
        }
        return f"{len(exc)} exceptions flagged"
