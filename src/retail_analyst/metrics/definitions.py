_LINES = (
    "Business definitions (use exactly these):",
    "- Revenue: SUM(order_items.sale_price), excluding order_items with status "
    "'Cancelled' or 'Returned'.",
    "- Margin: sale_price minus products.cost on the same items "
    "(order_items.product_id = products.id), over the items counted in revenue.",
    "- Average order value: revenue divided by the number of distinct "
    "order_items.order_id that contribute to that revenue.",
    "- Return rate: order_items with status 'Returned' divided by all order_items "
    "in the same period.",
    "- Churn: a customer who ordered before but has no non-cancelled order in the "
    "last 90 days, measured against today.",
    "- A total number of orders is COUNT(DISTINCT order_id) over the whole set; never add up "
    "the order counts of each group, because one order can hold items of several groups.",
    "- Give every metric asked for overall as well as by group, and use the overall figures "
    "to judge the direction of the change.",
    "- 'Last month' means the last complete calendar month, never the partial current month.",
    "- Comparisons use equal-length complete periods, for example the last "
    "complete month against the complete month before it.",
)


def metric_definitions() -> str:
    return "\n".join(_LINES) + "\n"
