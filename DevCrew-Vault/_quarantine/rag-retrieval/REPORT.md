# Validation Report — rag-retrieval
**Status:** invalid
## Errors
- Optional field 'allowed-tools' has wrong type (expected list, got str)
## Warnings
- Body is 16786 chars (>8000); consider moving large content to references/
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scripts\self-rag-graph.py line 221: 'async def decide_retrieval(state: SelfRAGState, config: SelfRAGConfig) -> dict:'
- [SAFETY] Pattern 'eval\\s*\\(' matched in scripts\scripts\self-rag-graph.py line 422: 'workflow.add_node("decide_retrieval", lambda s: decide_retrieval(s, config))'
