_P = "bigquery-public-data.thelook_ecommerce"

_LINES = (
    f"BigQuery dataset {_P}. Tables (always use fully qualified names):",
    "",
    f"{_P}.orders: order_id, user_id, status, gender, created_at, returned_at, "
    "shipped_at, delivered_at, num_of_item",
    f"{_P}.order_items: id, order_id, user_id, product_id, inventory_item_id, "
    "status, created_at, shipped_at, delivered_at, returned_at, sale_price",
    f"{_P}.products: id, cost, category, name, brand, retail_price, department, "
    "sku, distribution_center_id",
    f"{_P}.users: id, age, gender, state, country, city, traffic_source, created_at",
    "  city, state and country may only be used as GROUP BY dimensions of "
    "aggregates, never selected as raw rows.",
    "",
    "Join keys:",
    "- order_items.order_id = orders.order_id",
    "- order_items.product_id = products.id",
    "- orders.user_id = users.id",
    "- order_items.user_id = users.id",
    "",
    "Status values (orders.status and order_items.status): Shipped, Complete, "
    "Processing, Cancelled, Returned.",
    "",
    "users represents shoppers (customers of the shop), not the executives asking the questions.",
)


def schema_description() -> str:
    return "\n".join(_LINES) + "\n"
