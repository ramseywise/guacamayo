# Multi-Agent Knowledge Schema

*Working artifact from genesis Phase 6 engagement — 2026-07-13*

## Problem

Multi-agent systems need agents that track *why they believe what they believe*, not just *what they believe*. Most A2A protocols treat knowledge transfer as message-passing. Real metacognition and theory of mind require provenance, contradiction tracking, and a first-class representation of what each agent believes about the other's knowledge state.

## Design Principle

The librarian principle applied to A2A: every belief has a source, contradictions are flagged (never silently overwritten), and knowledge received from another agent is tracked as such.

## Schema

```python
@dataclass
class Belief:
    id: str
    content: Any
    source: Source
    confidence: float
    timestamp: datetime
    contradicts: list[str]    # belief_ids this conflicts with
    derived_from: list[str]   # belief_ids this was inferred from

@dataclass
class Source:
    type: Literal["observation", "agent_message", "inference", "tool_result"]
    agent_id: str | None   # if received from another agent
    task_id: str
    step: int

@dataclass
class PeerModel:
    """Agent A's model of what Agent B knows — theory of mind as data"""
    agent_id: str
    believed_beliefs: list[Belief]
    believed_capabilities: list[str]
    last_synced: datetime
    confidence: float   # how much A trusts its model of B

@dataclass
class MetaState:
    """Agent's model of its own knowledge state"""
    knowledge_gaps: list[str]      # known unknowns
    uncertain_beliefs: list[str]   # belief_ids flagged uncertain
    stale_beliefs: list[str]       # likely outdated
    attention_budget: AttentionBudget

@dataclass
class AttentionBudget:
    total_tokens: int
    used: int
    high_value_context: list[str]   # worth keeping in window
    compressible: list[str]         # can be summarized/offloaded

@dataclass
class AgentKnowledgeState:
    agent_id: str
    beliefs: list[Belief]
    task_state: TaskState
    peer_models: dict[str, PeerModel]   # keyed by agent_id
    meta: MetaState
```

## Communication Protocol

| Message | Carries | When to use |
|---------|---------|-------------|
| `KnowledgePush` | Beliefs + full provenance | When source chain matters to receiver |
| `BeliefCorrection` | Correction + reason | When a prior belief was wrong |
| `PeerModelSync` | A's model of B + sync request | When A needs to verify its theory of mind |
| `TaskHandoff` | Subtask + scoped context slice | Delegation |
| `AttentionBrief` | Compressed state, optimized for receiver | Default communication — most traffic |

## Key Tensions

- **Full provenance vs. token efficiency**: Tracking full source chains is expensive. `AttentionBrief` is the efficiency valve — most A2A communication goes through it; `KnowledgePush` is reserved for when provenance matters to the reasoning.
- **PeerModel staleness**: Agent A's model of Agent B drifts as B acts. The `confidence` field on PeerModel tracks trust in the model's currency; `PeerModelSync` is how A checks it.
- **Contradiction resolution**: Who resolves contradictions between agent beliefs? The schema flags them; the resolution policy is separate (could be orchestrator, could be explicit negotiation protocol).

## Open Questions

- How does the contradiction resolution policy work in practice? Does the receiving agent decide, or is there an arbitration layer?
- What's the right granularity for `AttentionBrief`? Task-level? Step-level? How does this interact with LangGraph's checkpoint mechanism?
- How do you represent uncertainty in PeerModel — not just "I think B knows X" but "I think B knows X with probability 0.7"?
- Can this schema plug into LangGraph's state graph natively, or does it need a wrapper?
