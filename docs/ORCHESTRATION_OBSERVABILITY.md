# Orchestration and Observability v0

Status: Jason-confirmed architecture direction.

## 1. LangGraph role

LangGraph is the orchestration runtime of Financial Research Workflow.

It coordinates product-level research stages.

It does not define:
- financial semantics;
- evidence meaning;
- analyst mandate;
- trading meaning;
- Quant Desk state.

Those remain explicit business contracts.

The v0 workflow is deliberately bounded:

    START
      ->
    validate_request
      ->
    resolve_scope
      ->
    collect_evidence
      ->
    fundamental_analyst
      ->
    claim_review
      -> PASS -> publish
      -> PARTIAL -> publish_partial
      -> FAIL -> preserve_failure
      ->
    END

v0 has no autonomous planner, no unrestricted routing, and no unlimited
agent-to-agent conversation.

## 2. Outer graph vs Evidence Service graph

The Financial Research LangGraph is the outer product workflow.

The existing Retrieval Lab may continue to use its own bounded graph internally
for Evidence Service R&D.

Conceptually:

    Financial Research Workflow graph
        ->
    Evidence Service interface
        ->
    selected bounded retrieval runtime

These graphs serve different responsibilities.

The new repository must not create a second retrieval engine while B1 remains
open.

## 3. Business state is independent of LangGraph

Core business objects must not depend on LangGraph-specific state semantics.

The authoritative logical research state contains objects such as:

    ResearchState
    - ResearchRequest
    - resolved execution scope
    - EvidencePacket(s)
    - FundamentalResearchOutput
    - ClaimReviewResult
    - runtime status
    - provenance
    - research_run_id

LangGraph moves these objects through workflow stages.

If the orchestration technology changes later, the research contracts should
remain valid.

## 4. LangGraph Studio

LangGraph Studio is a development and debugging surface.

It may be used to inspect:
- graph topology;
- node execution;
- state transitions;
- routing;
- failures;
- development runs.

Studio is not the end-user AI Research Department UI.

The product UI must present research meaning:
- findings;
- evidence;
- outlook;
- risks;
- conflicts;
- limitations;
- review status;
- provenance.

## 5. LangSmith

LangSmith is an optional future observability and evaluation layer.

Potential uses include:
- execution tracing;
- latency;
- token usage;
- node failures;
- model/config identity;
- regression analysis;
- evaluation support.

LangSmith must not become a runtime requirement.

A missing LangSmith connection, API key, or tracing service must not prevent a
research run from completing.

## 6. Authoritative record

The system's own ResearchRun artifact is authoritative.

Conceptually:

    LangGraph execution
        -> ResearchRun artifact
             authoritative research record
        -> optional LangSmith trace
             observability copy

LangSmith traces do not replace:
- ResearchRequest;
- EvidencePacket;
- analyst output;
- review result;
- provenance;
- deterministic calculation records.

## 7. Trace privacy boundary

Tracing must not silently expand the information boundary of the research
system.

Safe-by-default trace metadata may include:
- research_run_id;
- graph/node name;
- runtime status;
- duration;
- model identifier;
- token counts;
- corpus/index identifier;
- document identifiers;
- evidence counts;
- claim identifiers;
- review result;
- error class.

Potentially sensitive payloads require explicit policy before external tracing:
- raw report/document spans;
- full source documents;
- private research notes;
- portfolio context;
- proprietary corpora;
- credentials;
- user-private material.

Do not enable broad payload tracing merely because Studio or LangSmith supports
it.

## 8. Development sequence

The implementation order is:

1. freeze contracts;
2. implement typed contract models;
3. implement bounded LangGraph workflow using a fake Evidence provider;
4. expose the graph to LangGraph Studio;
5. implement Fundamental Analyst and Claim Review;
6. build product UI;
7. after B1 closure, integrate selected stable Evidence Service runtime;
8. later enable LangSmith tracing under an explicit trace policy.

This sequence prevents orchestration tooling from determining business
semantics.


## 9. Local development environment

Studio tooling is isolated from the product runtime dependency set.

Dependency groups:

- runtime: LangGraph and typed business contracts;
- dev: test tooling;
- studio: LangGraph CLI / Studio tooling;
- tracing: optional LangSmith tooling.

A Studio tooling installation failure must not block development or execution
of the Financial Research Workflow core.

On the initial Intel macOS x86_64 development machine, the current Studio CLI
dependency chain requires a cryptography source build because the selected
cryptography release does not provide a compatible macOS x86_64 wheel.
Therefore Studio tooling is not installed in the core venv at this stage.

Do not weaken or pin product runtime dependencies merely to make Studio tooling
install. Resolve Studio as an independent development-environment concern.
