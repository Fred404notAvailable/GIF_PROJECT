---
name: langgraph-cyclic-state-machine
description: >
  Builds multi-step AI agents with cyclic workflows using LangGraph (Python).
  Use when building an agent that needs to loop, retry, or branch based on LLM
  output — including ReAct-style tool-use agents, multi-agent orchestration, or
  workflows where the LLM decides next steps. Invoke when the pipeline has
  conditional branching, requires human-in-the-loop interrupts, or needs
  persistent state across turns. Do not use for simple linear chains (use
  LangChain LCEL), one-shot LLM calls, or fully deterministic pipelines without
  branching.
license: MIT
compatibility:
  - claude-3-5-sonnet
  - gpt-4o
metadata:
  origin: authored
  review_status: needs-human-review
allowed-tools:
  - read_file
  - write_file
  - run_command
---

# LangGraph Cyclic State Machine Agent

## When to Use / When Not to Use

### Use When
- Building an agent that needs to **loop, retry, or branch** based on LLM output.
- Implementing a **ReAct-style agent** (Reason + Act) with tool calls and observation cycles.
- **Multi-agent orchestration** — a supervisor routes work to specialized subgraph agents.
- The workflow requires **human-in-the-loop** approval at certain steps.
- You need **persistent state** across multiple conversation turns (checkpointing).
- The agent must decide **dynamically** which node to visit next.

### Do NOT Use When
- The pipeline is **linear and deterministic** — use LangChain LCEL (`chain = prompt | llm | parser`).
- You need a **one-shot LLM call** — call the model directly.
- The "branching" is purely **rule-based with no LLM involvement** — use standard Python control flow.
- You need a **simple RAG pipeline** — a single retriever + LLM chain is sufficient.

---

## Procedure

### 1. Install Dependencies

```bash
pip install langgraph langchain-openai langchain-core
# For persistence:
pip install langgraph-checkpoint-sqlite  # or langgraph-checkpoint-postgres
```

### 2. Define the State Schema

Use `TypedDict` from `typing`. **All state fields must be declared upfront.** Use `Annotated` with `operator.add` for lists that nodes append to (message history pattern):

```python
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Annotated with operator.add → nodes append, not overwrite
    messages: Annotated[list[BaseMessage], operator.add]
    # Regular fields → nodes replace by returning new value
    plan: str
    search_queries: list[str]
    search_results: list[str]
    answer: str
    iteration_count: int
    is_sufficient: bool
```

> **Rule:** Never mutate the state dict in-place. Always return a **new dict** with only the keys you are updating. LangGraph merges the returned dict with the existing state.

### 3. Write Node Functions

Each node is a plain Python function that accepts the full state and returns a partial state dict:

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def plan_node(state: AgentState) -> dict:
    """Generate search queries based on the user's question."""
    response = llm.invoke([
        HumanMessage(content=f"Generate 2-3 search queries to answer: {state['messages'][-1].content}")
    ])
    queries = parse_queries(response.content)  # your parsing logic
    return {
        "plan": response.content,
        "search_queries": queries,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }

def search_node(state: AgentState) -> dict:
    """Execute all planned search queries."""
    results = []
    for query in state["search_queries"]:
        result = web_search(query)  # your search tool
        results.append(result)
    return {"search_results": results}

def evaluate_node(state: AgentState) -> dict:
    """Decide if search results are sufficient to answer the question."""
    response = llm.invoke([
        HumanMessage(content=(
            f"Question: {state['messages'][-1].content}\n"
            f"Results: {state['search_results']}\n"
            "Is this sufficient to give a complete answer? Reply YES or NO and explain."
        ))
    ])
    is_sufficient = response.content.strip().upper().startswith("YES")
    return {"is_sufficient": is_sufficient}

def answer_node(state: AgentState) -> dict:
    """Generate the final answer from collected results."""
    response = llm.invoke([
        HumanMessage(content=(
            f"Question: {state['messages'][-1].content}\n"
            f"Research: {state['search_results']}\n"
            "Provide a comprehensive answer."
        ))
    ])
    return {
        "answer": response.content,
        "messages": [AIMessage(content=response.content)],
    }
```

### 4. Build the Graph

```python
from langgraph.graph import StateGraph, START, END

# Initialize graph with state schema
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("plan", plan_node)
graph_builder.add_node("search", search_node)
graph_builder.add_node("evaluate", evaluate_node)
graph_builder.add_node("answer", answer_node)

# Add deterministic edges
graph_builder.add_edge(START, "plan")
graph_builder.add_edge("plan", "search")
graph_builder.add_edge("search", "evaluate")

# Add conditional edge — the cycle or exit decision
def should_continue(state: AgentState) -> str:
    if state.get("is_sufficient", False):
        return "answer"
    if state.get("iteration_count", 0) >= 3:
        return "answer"  # safety: don't loop more than 3 times
    return "plan"  # loop back

graph_builder.add_conditional_edges(
    "evaluate",             # from this node
    should_continue,        # routing function
    {                       # mapping of return values → node names
        "answer": "answer",
        "plan": "plan",
    }
)
graph_builder.add_edge("answer", END)
```

### 5. Add Checkpointing (Persistence)

```python
from langgraph.checkpoint.memory import MemorySaver
# For production, use SqliteSaver or PostgresSaver

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)
```

For SQLite persistence:
```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("agent_state.db") as checkpointer:
    graph = graph_builder.compile(checkpointer=checkpointer)
```

### 6. Human-in-the-Loop Interrupts

```python
graph = graph_builder.compile(
    checkpointer=memory,
    interrupt_before=["answer"],  # pause before answer node for human review
)

# Run until interrupt
config = {"configurable": {"thread_id": "user-123"}}
for event in graph.stream(initial_state, config):
    print(event)

# Human reviews, then resume
graph.update_state(config, {"approved": True})
for event in graph.stream(None, config):  # None = resume from checkpoint
    print(event)
```

### 7. Run the Graph

```python
# Single invocation
initial_state = {
    "messages": [HumanMessage(content="What are the latest developments in LangGraph?")],
    "iteration_count": 0,
    "is_sufficient": False,
}

config = {"configurable": {"thread_id": "session-001"}, "recursion_limit": 15}

# Streaming execution (recommended)
for event in graph.stream(initial_state, config, stream_mode="values"):
    print(event)

# Or full execution
result = graph.invoke(initial_state, config)
print(result["answer"])
```

### 8. Configure Recursion Limit

The default recursion limit is 25. Always set it explicitly:

```python
config = {
    "recursion_limit": 10,         # max total node executions
    "configurable": {"thread_id": "abc"},
}
```

Exceeding this raises `GraphRecursionError`. Always have a cycle-breaker condition in your routing function (e.g., `iteration_count >= N → exit`).

---

## Checklist

- [ ] State schema defined as `TypedDict` with all fields declared
- [ ] List fields that accumulate use `Annotated[list[...], operator.add]`
- [ ] Every node function returns a **new partial dict** (never mutates `state` in-place)
- [ ] All nodes added with `add_node()`
- [ ] Every node has at least one outgoing edge (no dead ends)
- [ ] Conditional edges cover **all possible return values** of the routing function
- [ ] A **cycle-breaker** condition exists (iteration counter, max retries) preventing infinite loops
- [ ] `recursion_limit` set explicitly in config
- [ ] `START` and `END` constants used (not strings `"__start__"`)
- [ ] Checkpointer configured if state needs to persist across sessions
- [ ] Error handling inside nodes (tool failures should update state, not crash the graph)
- [ ] `thread_id` passed in config for stateful/multi-turn graphs

---

## Common Pitfalls

| Pitfall | Example | Fix |
|---|---|---|
| **Mutating state in-place** | `state["count"] += 1; return state` | Return `{"count": state["count"] + 1}` — a new partial dict |
| **Missing edge from a node** | `plan` node has no outgoing edge | Every node must connect to another node or `END` |
| **Uncovered conditional branch** | Routing returns `"retry"` but it's not in the mapping dict | List all possible return values in the mapping |
| **Hitting recursion limit** | No `iteration_count` guard in a loop | Add counter to state; routing function exits when count exceeds threshold |
| **Not handling tool errors** | Tool raises exception → graph crashes | Wrap tool calls in try/except; store error in state; route accordingly |
| **No `thread_id` for stateful graph** | Checkpointer configured but no `thread_id` in config | Always pass `{"configurable": {"thread_id": "..."}}` |
| **Parallel node mutation** | Two nodes both write to same non-annotated field | Use `Annotated` with a reducer, or ensure only one node writes to each field |

---

## Worked Example: Research Agent

**Goal:** An agent that plans search queries, executes them, evaluates sufficiency, and either loops for more research or generates a final answer.

**Flow:**
```
START → plan → search → evaluate → (sufficient?) → answer → END
                            ↑                           |
                            └──── (not sufficient) ─────┘
                                  (loop back to plan)
```

The complete annotated implementation is in `references/deep-dive.md`, including:
- Full state schema with all fields
- All node implementations
- Supervisor multi-agent pattern
- Persistence and checkpointing guide

See `references/deep-dive.md` for detailed reference material.
