"""WF001 — Inventory Restock Check
Excel steps: Load inventory → compare stock with threshold → identify low-stock → calculate reorder qty → restock list
Decision: If current_stock < minimum_stock, mark product for restock
"""
from engine.executor import BaseHandler, step


class InventoryRestock(BaseHandler):
    workflow_id = "WF001"

    @step("Load inventory")
    def load(self):
        df = self.use("csv_reader")(self.inputs.get("file", "inventory.csv"))
        self.state["df"] = df
        return f"{len(df)} products loaded"

    @step("Compare current stock with minimum threshold")
    def compare(self):
        df = self.state["df"]
        df["needs_restock"] = df["current_stock"] < df["minimum_stock"]
        return f"{int(df['needs_restock'].sum())} below threshold"

    @step("Identify low-stock products")
    def identify(self):
        self.state["low"] = self.state["df"][self.state["df"]["needs_restock"]].copy()
        return ", ".join(self.state["low"]["product_name"].tolist()) or "none"

    @step("Calculate reorder quantity")
    def reorder(self):
        low = self.state["low"]
        # reorder enough to reach 2x the minimum (simple business rule)
        low["suggested_reorder_qty"] = (low["minimum_stock"] * 2 - low["current_stock"]).astype(int)
        self.use("calculator")
        return "reorder qty = (2 × minimum) − current"

    @step("Generate restock list")
    def report(self):
        low = self.state["low"]
        self.state["output"] = {
            "products_requiring_restock": low[["sku", "product_name", "current_stock",
                                               "minimum_stock", "suggested_reorder_qty"]].to_dict("records"),
            "count": len(low),
        }
        return f"{len(low)} items in restock list"
