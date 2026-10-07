"""WF005 — Customer Order Status
Steps: Validate identifier → search order → retrieve status → retrieve shipment → summarize
Decision: If no order is found, ask for another identifier
"""
import re
from engine.executor import BaseHandler, step
from engine.models import NeedsInput


class OrderStatus(BaseHandler):
    workflow_id = "WF005"

    @step("Validate identifier")
    def validate(self):
        ident = self.inputs.get("identifier")
        if not ident:  # try to pull ORD-xxxx or an email from the request text itself
            m = re.search(r"\b(ORD-\d+)\b", self.request, re.I) or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", self.request)
            ident = m.group(0) if m else None
        if not ident:
            raise NeedsInput("Please provide an Order ID (e.g. ORD-1001) or the customer's email address.")
        self.state["ident"] = ident
        return f"identifier = {ident}"

    @step("Search order data")
    def search(self):
        order = self.use("order_database")(self.state["ident"])
        if order is None:
            raise NeedsInput(f"No order found for '{self.state['ident']}'. Please provide another Order ID or email.")
        self.state["order"] = order
        return f"found {order['order_id']} for {order['customer_email']}"

    @step("Retrieve order status")
    def status(self):
        return f"status = {self.state['order']['status']}"

    @step("Retrieve shipment information")
    def shipment(self):
        ship = self.use("shipment_lookup")(self.state["order"]["order_id"])
        self.state["shipment"] = ship
        return f"carrier = {ship['carrier']}, tracking = {ship['tracking_number']}" if ship else "not shipped yet"

    @step("Summarize current status")
    def summarize(self):
        o, s = self.state["order"], self.state["shipment"]
        self.state["output"] = {
            "order_id": o["order_id"], "customer_email": o["customer_email"],
            "items": o["items"], "order_status": o["status"], "order_date": o["order_date"],
            "shipment": s or "No shipment record yet",
            "summary": f"Order {o['order_id']} is {o['status']}." +
                       (f" Shipped via {s['carrier']} (tracking {s['tracking_number']}), status: {s['shipment_status']}, ETA {s['eta']}." if s else ""),
        }
        return self.state["output"]["summary"]
