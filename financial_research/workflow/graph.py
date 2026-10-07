from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from financial_research.contracts import ReviewStatus
from financial_research.state import ResearchRunStatus, ResearchState
from financial_research.workflow.interfaces import WorkflowServices


def _require_run_id(state: ResearchState) -> str:
    run_id = state.get("research_run_id")
    if not run_id:
        raise ValueError("research_run_id is required")
    return run_id


def build_research_graph(services: WorkflowServices):
    def validate_request(state: ResearchState) -> dict:
        _require_run_id(state)

        if "request" not in state:
            raise ValueError("request is required")

        return {
            "run_status": ResearchRunStatus.VALIDATED,
        }

    def resolve_scope(state: ResearchState) -> dict:
        run_id = _require_run_id(state)

        scope = services.scope_resolver.resolve(
            state["request"],
            run_id,
        )

        return {
            "execution_scope": scope,
            "run_status": ResearchRunStatus.SCOPE_RESOLVED,
        }

    def collect_evidence(state: ResearchState) -> dict:
        run_id = _require_run_id(state)

        packets = services.evidence_provider.collect(
            state["request"],
            state["execution_scope"],
            run_id,
        )

        for packet in packets:
            if packet.research_run_id != run_id:
                raise ValueError(
                    "EvidencePacket research_run_id does not match workflow run"
                )

        request_question_ids = {
            question.question_id
            for question in state["request"].research_questions
        }

        packet_question_ids = {
            packet.question_id
            for packet in packets
        }

        unknown_questions = packet_question_ids - request_question_ids

        if unknown_questions:
            raise ValueError(
                "EvidencePacket references unknown question IDs: "
                f"{sorted(unknown_questions)}"
            )

        return {
            "evidence_packets": packets,
            "run_status": ResearchRunStatus.EVIDENCE_COLLECTED,
        }

    def fundamental_analyst(state: ResearchState) -> dict:
        run_id = _require_run_id(state)

        draft = services.fundamental_analyst.analyze(
            state["request"],
            state["evidence_packets"],
            run_id,
        )

        if draft.research_run_id != run_id:
            raise ValueError(
                "FundamentalResearchDraft research_run_id does not match workflow run"
            )

        return {
            "draft": draft,
            "run_status": ResearchRunStatus.DRAFTED,
        }

    def claim_review(state: ResearchState) -> dict:
        run_id = _require_run_id(state)

        review = services.claim_reviewer.review(
            state["draft"],
            state["evidence_packets"],
            run_id,
        )

        if review.research_run_id != run_id:
            raise ValueError(
                "ClaimReviewResult research_run_id does not match workflow run"
            )

        return {
            "review_result": review,
            "run_status": ResearchRunStatus.REVIEWED,
        }

    def route_review(state: ResearchState) -> str:
        status = state["review_result"].status

        if status == ReviewStatus.PASS:
            return "publish"

        if status == ReviewStatus.PARTIAL:
            return "publish_partial"

        if status == ReviewStatus.FAIL:
            return "preserve_failure"

        raise ValueError(f"unsupported review status: {status}")

    def publish(state: ResearchState) -> dict:
        return {
            "run_status": ResearchRunStatus.PUBLISHED,
        }

    def publish_partial(state: ResearchState) -> dict:
        return {
            "run_status": ResearchRunStatus.PARTIAL,
        }

    def preserve_failure(state: ResearchState) -> dict:
        reasons = state["review_result"].reasons

        return {
            "run_status": ResearchRunStatus.FAILED,
            "failure_reason": "; ".join(reasons) if reasons else "Claim Review failed",
        }

    builder = StateGraph(ResearchState)

    builder.add_node("validate_request", validate_request)
    builder.add_node("resolve_scope", resolve_scope)
    builder.add_node("collect_evidence", collect_evidence)
    builder.add_node("fundamental_analyst", fundamental_analyst)
    builder.add_node("claim_review", claim_review)
    builder.add_node("publish", publish)
    builder.add_node("publish_partial", publish_partial)
    builder.add_node("preserve_failure", preserve_failure)

    builder.add_edge(START, "validate_request")
    builder.add_edge("validate_request", "resolve_scope")
    builder.add_edge("resolve_scope", "collect_evidence")
    builder.add_edge("collect_evidence", "fundamental_analyst")
    builder.add_edge("fundamental_analyst", "claim_review")

    builder.add_conditional_edges(
        "claim_review",
        route_review,
        {
            "publish": "publish",
            "publish_partial": "publish_partial",
            "preserve_failure": "preserve_failure",
        },
    )

    builder.add_edge("publish", END)
    builder.add_edge("publish_partial", END)
    builder.add_edge("preserve_failure", END)

    return builder.compile()
