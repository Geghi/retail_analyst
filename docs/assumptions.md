# Assumptions and open questions

Decisions the brief leaves open.
Each one has our default and what changes if the client disagrees.
Open questions are marked **Open**.

## Data

The data source is the Google public dataset `bigquery-public-data.thelook_ecommerce`.
It is read-only and contains fake shoppers, not the executives who use the agent.
Data runs from January 2019 to the current day, so it keeps growing.

## Decisions

| Topic | Default | If the client disagrees |
| ----- | ------- | ----------------------- |
| Churn | A customer who ordered before but has no non-cancelled order in the last 90 days, measured against today. | Change the window or the signal in the metric definitions. |
| Revenue | Sum of `order_items.sale_price`, excluding `Cancelled` and `Returned` items. | Change the one metric definition the agent shares. |
| "Last month" | The last complete calendar month. The current partial month is never compared with a full one. | Change the date rule in the metric definitions. |
| User to product | Simulated executives in a config file, each limited to some product categories. The backend adds the filter to every query. | Production reads the mapping from the identity provider or a permissions table. |
| PII | `user_id` allowed. City, state and country allowed only inside aggregates. Names, emails, street addresses, postal codes and coordinates never shown. | Widen or narrow the blocked column list. |
| Golden Bucket | Simulated with a few invented question, SQL and report trios in `golden/`. | A real bucket replaces the files; the retrieval code stays. |
| Promotion to Golden | Never automatic. A new analysis becomes a candidate, and an analyst approves it. | Auto-promote only narrow, deterministic analyses that pass validation. |
| Report deletion | Soft delete, recoverable for 30 days, always after an explicit confirmation. | Switch to permanent deletion; the confirmation step stays. |

## Open

- **Golden Bucket.** Does a real bucket exist, or should we keep simulating it?
- **Promotion.** Do new analyses need analyst approval before joining the bucket?
- **Product scope.** Should an executive's products be defined by category, department or brand?
