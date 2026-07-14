"""State-machine transition maps: every listed edge passes, every unlisted edge
raises (parameterized, Section U/J)."""
import itertools

import pytest

from jobsearch_os import state_machine as sm


@pytest.mark.parametrize("machine", list(sm.MACHINES.keys()))
def test_listed_edges_pass(machine):
    for frm, to in sm.listed_edges(machine):
        assert sm.can(machine, frm, to), f"{machine}: {frm}->{to} should be allowed"


@pytest.mark.parametrize("machine", list(sm.MACHINES.keys()))
def test_unlisted_edges_raise(machine):
    states = sm.all_states(machine)
    listed = set(sm.listed_edges(machine))
    for frm, to in itertools.product(states, states):
        if (frm, to) in listed:
            continue
        with pytest.raises(sm.InvalidTransition):
            sm.assert_transition(machine, frm, to)


def test_rejected_and_deferred_cannot_reach_submission():
    # packet: rejected/closed cannot jump to submission_assist_ready
    assert not sm.can("packet", "rejected", "submission_assist_ready")
    assert not sm.can("packet", "closed", "submission_assist_ready")
    # job: a scored job cannot jump straight to submitted_logged
    assert not sm.can("job", "scored", "submitted_logged")


def test_job_universal_exception_edges():
    assert sm.can("job", "scored", "blocked")
    assert sm.can("job", "approval_pending", "withdrawn")
    # terminal states have no exception exits
    assert not sm.can("job", "closed", "blocked")
