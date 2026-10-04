"""Tiny stand-in for langgraph.graph, ONLY for offline testing (real LangGraph not installable here)."""
import sys, types

START, END = "__start__", "__end__"

class StateGraph:
    def __init__(self, _state): self.nodes, self.edges, self.cond = {}, {}, {}
    def add_node(self, n, f): self.nodes[n] = f
    def add_edge(self, a, b): self.edges[a] = b
    def add_conditional_edges(self, a, fn, mapping): self.cond[a] = (fn, mapping)
    def compile(self): return self
    def invoke(self, state):
        state = dict(state); cur = self.edges[START]
        while cur != END:
            state.update(self.nodes[cur](state) or {})
            if cur in self.cond:
                fn, m = self.cond[cur]; cur = m[fn(state)]
            else:
                cur = self.edges[cur]
        return state

mod = types.ModuleType("langgraph"); g = types.ModuleType("langgraph.graph")
g.StateGraph, g.START, g.END = StateGraph, START, END
sys.modules["langgraph"], sys.modules["langgraph.graph"] = mod, g
