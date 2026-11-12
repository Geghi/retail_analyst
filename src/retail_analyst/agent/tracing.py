import time

from langchain_core.callbacks import BaseCallbackHandler

from retail_analyst import settings


class TraceCallback(BaseCallbackHandler):
    def __init__(self, turn):
        self.turn = turn
        self.started: dict = {}

    def node_name(self, metadata, kwargs):
        node = (metadata or {}).get("langgraph_node")
        return node if node and kwargs.get("name") == node else None

    def on_chain_start(self, serialized, inputs, *, run_id, metadata=None, **kwargs):
        node = self.node_name(metadata, kwargs)
        if node:
            self.started[run_id] = (node, time.perf_counter())

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        self.finish_node(run_id, ok=True)

    def on_chain_error(self, error, *, run_id, **kwargs):
        self.finish_node(run_id, ok=False, error=type(error).__name__)

    def finish_node(self, run_id, **fields):
        started = self.started.pop(run_id, None)
        if started:
            node, begun = started
            duration_ms = round((time.perf_counter() - begun) * 1000, 1)
            self.turn.event(node, duration_ms=duration_ms, **fields)

    def on_llm_end(self, response, **kwargs):
        message = response.generations[0][0].message
        usage = message.usage_metadata or {}
        model = message.response_metadata.get("model_name")
        input_tokens, output_tokens = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        self.turn.event(
            "llm",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=usage.get("total_tokens", 0),
            cost_usd=settings.cost_usd(model, input_tokens, output_tokens),
        )
