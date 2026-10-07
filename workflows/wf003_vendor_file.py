"""WF003 — Vendor File Processing
Steps: Read file → detect columns → normalize names → validate required → invalid rows → cleaned dataset
Decision: Rows missing SKU or product name are invalid
"""
import re
from engine.executor import BaseHandler, step
from engine.tools import DATA_DIR

REQUIRED = ["sku", "product_name"]
# common vendor spellings → our canonical names
ALIASES = {"item_code": "sku", "sku_code": "sku", "product": "product_name", "name": "product_name",
           "item_name": "product_name", "cost": "price", "unit_price": "price", "qty": "quantity"}


class VendorFileProcessing(BaseHandler):
    workflow_id = "WF003"

    @step("Read file")
    def read(self):
        f = self.inputs.get("file", "vendor_upload.csv")
        self.state["df"] = self.use("csv_reader")(f)
        return f"{len(self.state['df'])} rows read from {f}"

    @step("Detect columns")
    def detect(self):
        self.state["original_cols"] = list(self.state["df"].columns)
        return ", ".join(self.state["original_cols"])

    @step("Normalize column names")
    def normalize(self):
        df = self.state["df"]
        new = {}
        for c in df.columns:
            key = re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_")
            new[c] = ALIASES.get(key, key)
        df.rename(columns=new, inplace=True)
        return " | ".join(f"{k}→{v}" for k, v in new.items() if k != v) or "already clean"

    @step("Validate required fields")
    def validate(self):
        df = self.state["df"]
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise ValueError(f"Required column(s) not found even after normalisation: {missing}")
        return "required columns present"

    @step("Identify invalid rows")
    def invalid(self):
        df = self.state["df"]
        bad_mask = df[REQUIRED].isna().any(axis=1) | (df[REQUIRED].astype(str).apply(lambda s: s.str.strip() == "")).any(axis=1)
        bad = df[bad_mask].copy()
        bad["reason"] = bad.apply(lambda r: "missing " + ", ".join(c for c in REQUIRED if not str(r[c]).strip() or str(r[c]) == "nan"), axis=1)
        self.state["bad"], self.state["good"] = bad, df[~bad_mask]
        return f"{len(bad)} invalid rows"

    @step("Produce cleaned dataset")
    def produce(self):
        out = DATA_DIR.parent.parent / "examples" / "outputs" / "vendor_cleaned.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        self.state["good"].to_csv(out, index=False)
        self.state["output"] = {
            "cleaned_file": str(out.relative_to(DATA_DIR.parent.parent)),
            "summary": {"total_rows": len(self.state["df"]), "valid_rows": len(self.state["good"]),
                        "invalid_rows": len(self.state["bad"]), "columns_normalized": self.state["original_cols"]},
            "invalid_row_report": self.state["bad"].fillna("").to_dict("records"),
        }
        return f"cleaned file saved → {out.name}"
