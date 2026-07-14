"""State machines as data (Section J), not scattered `if` statements.

Each machine is an explicit transition map. `assert_transition` raises on any
edge not in the map. The Job machine additionally allows the universal
exception edges from any non-terminal state (per the spec). The listed edges
are exhaustive — no others exist.
"""
from __future__ import annotations


class InvalidTransition(ValueError):
    pass


# Universal exception/terminal targets — Job machine only (Section J).
JOB_EXCEPTION_STATES = {"duplicate", "blocked", "stale", "withdrawn", "error"}

JOB_TERMINAL = {
    "closed", "accepted", "declined", "rejected",
    "duplicate", "blocked", "stale", "withdrawn", "error",
}

JOB: dict[str, set[str]] = {
    "new": {"normalized"},
    "normalized": {"deduped"},
    "deduped": {"scored"},
    "scored": {"packet_ready", "research_ready"},
    "research_ready": {"research_done"},
    "research_done": {"packet_ready"},
    "packet_ready": {"approval_pending"},
    "approval_pending": {"approved_to_apply"},
    "approved_to_apply": {"submission_assist_ready"},
    "submission_assist_ready": {"submitted_logged"},
    "submitted_logged": {"followup_due"},
    "followup_due": {"reply_received", "closed"},
    "reply_received": {"interview", "rejected", "closed"},
    "interview": {"offer", "rejected", "withdrawn", "closed"},
    "offer": {"accepted", "declined", "closed"},
}

PACKET: dict[str, set[str]] = {
    "drafting": {"quality_check"},
    "quality_check": {"packet_ready", "drafting"},
    "packet_ready": {"approval_pending"},
    "approval_pending": {"approved", "revise", "rejected", "deferred"},
    "approved": {"submission_assist_ready"},
    "revise": {"drafting"},
    "rejected": {"closed"},
    "deferred": {"approval_pending"},
    "submission_assist_ready": {"submitted_logged"},
    "submitted_logged": {"followup_due"},
    "followup_due": {"closed"},
}

OUTREACH: dict[str, set[str]] = {
    "contact_candidate": {"validated"},
    "validated": {"draft_ready"},
    "draft_ready": {"quality_check"},
    "quality_check": {"approval_pending", "draft_ready"},
    "approval_pending": {"approved", "revise", "rejected", "deferred"},
    "approved": {"sent_logged"},
    "revise": {"draft_ready"},
    "rejected": {"closed"},
    "deferred": {"approval_pending"},
    "sent_logged": {"followup_due"},
    "followup_due": {"reply_received", "closed"},
    "reply_received": {"closed", "do_not_contact"},
}

REPLY: dict[str, set[str]] = {
    "received": {"classified"},
    "classified": {"response_drafted"},
    "response_drafted": {"approval_pending"},
    "approval_pending": {"approved", "revise", "rejected", "deferred"},
    "approved": {"sent_logged"},
    "revise": {"response_drafted"},
    "rejected": {"closed"},
    "deferred": {"approval_pending"},
    "sent_logged": {"closed"},
}

MACHINES = {"job": JOB, "packet": PACKET, "outreach": OUTREACH, "reply": REPLY}


def _allowed(machine_name: str, from_state: str, to_state: str) -> bool:
    machine = MACHINES[machine_name]
    if to_state in machine.get(from_state, set()):
        return True
    if machine_name == "job":
        if to_state in JOB_EXCEPTION_STATES and from_state not in JOB_TERMINAL:
            return True
    return False


def can(machine_name: str, from_state: str, to_state: str) -> bool:
    if machine_name not in MACHINES:
        raise KeyError(f"Unknown machine: {machine_name}")
    return _allowed(machine_name, from_state, to_state)


def assert_transition(machine_name: str, from_state: str, to_state: str) -> None:
    if not can(machine_name, from_state, to_state):
        raise InvalidTransition(
            f"{machine_name}: {from_state!r} -> {to_state!r} is not a permitted transition"
        )


def listed_edges(machine_name: str) -> list[tuple[str, str]]:
    machine = MACHINES[machine_name]
    edges = [(f, t) for f, tos in machine.items() for t in tos]
    if machine_name == "job":
        for f in machine:
            if f not in JOB_TERMINAL:
                for exc in JOB_EXCEPTION_STATES:
                    edges.append((f, exc))
    return edges


def all_states(machine_name: str) -> set[str]:
    machine = MACHINES[machine_name]
    states = set(machine.keys())
    for tos in machine.values():
        states |= tos
    if machine_name == "job":
        states |= JOB_EXCEPTION_STATES
    return states
