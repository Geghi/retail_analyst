from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from retail_analyst.warehouse import WarehouseUnavailable

from .analysis_nodes import AnalysisNodes
from .deps import AgentDeps
from .report_nodes import ReportNodes
from .state import AgentState


def build_graph(deps: AgentDeps):
    analysis, reporting = AnalysisNodes(deps), ReportNodes(deps)
    warehouse_retry = RetryPolicy(
        max_attempts=3,
        initial_interval=deps.retry_interval,
        jitter=False,
        retry_on=WarehouseUnavailable,
    )
    builder = StateGraph(AgentState)
    builder.add_node("load_context", analysis.load_context)
    builder.add_node("plan", analysis.plan)
    builder.add_node("run_queries", analysis.run_queries, retry_policy=warehouse_retry)
    builder.add_node("analyze", analysis.analyze)
    builder.add_node("schema_answer", analysis.schema_answer)
    builder.add_node("give_up", analysis.give_up)
    builder.add_node("refuse", analysis.refuse)
    builder.add_node("save_report", reporting.save_report)
    builder.add_node("request_delete", reporting.request_delete)
    builder.add_node("confirm", reporting.confirm)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "plan")
    plan_targets = ["run_queries", "schema_answer", "save_report", "request_delete"]
    builder.add_conditional_edges(
        "plan", analysis.after_plan, [*plan_targets, "plan", "give_up", "refuse"]
    )
    builder.add_conditional_edges("run_queries", analysis.after_run, ["analyze", "plan", "give_up"])
    builder.add_conditional_edges("analyze", analysis.after_analyze, ["run_queries", END])
    builder.add_conditional_edges("request_delete", reporting.after_request, ["confirm", END])
    for terminal in ("schema_answer", "give_up", "refuse", "save_report", "confirm"):
        builder.add_edge(terminal, END)
    return builder.compile(checkpointer=InMemorySaver())
