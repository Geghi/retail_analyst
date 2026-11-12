from . import summarize


def render(summary: dict) -> str:
    lines = [
        f"{'turns':<20}{summary['turns']}",
        f"{'failure rate':<20}{summary['failure_rate']:.1%}",
        f"{'refusals':<20}{summary['refusals']}",
        f"{'retries':<20}{summary['retries']}",
        f"{'model calls':<20}{summary['tokens']['calls']}",
        f"{'tokens in':<20}{summary['tokens']['input']}",
        f"{'tokens out':<20}{summary['tokens']['output']}",
        "",
        "outcomes",
        *[f"  {name:<18}{count}" for name, count in summary["outcomes"].items()],
        "",
        f"{'step':<20}{'count':>7}{'p50 ms':>10}{'p95 ms':>10}",
        *[
            f"{name:<20}{s['count']:>7}{s['p50']:>10}{s['p95']:>10}"
            for name, s in summary["steps"].items()
        ],
        "",
        "errors by type",
        *[f"  {name:<18}{count}" for name, count in summary["errors_by_type"].items()],
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(summarize()))
