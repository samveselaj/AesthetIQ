from app.services.rules_engine import apply_rules


def test_opt_out_stop_exact():
    assert apply_rules("STOP").opt_out is True
    assert apply_rules("stop").opt_out is True
    assert apply_rules("Unsubscribe").opt_out is True


def test_opt_out_not_false_positive():
    # "stop by" in a sentence should NOT count as opt-out
    assert apply_rules("Can I stop by tomorrow?").opt_out is False


def test_medical_keyword_escalates():
    r = apply_rules("I have swelling after my filler")
    assert r.needs_escalation is True
    assert r.escalation_reason.startswith("medical_keyword:")


def test_complaint_escalates():
    r = apply_rules("I want a refund and will post a bad review")
    assert r.needs_escalation is True
    assert r.escalation_reason.startswith("complaint_keyword:")


def test_existing_appointment_escalates():
    r = apply_rules("Can I reschedule my appointment?")
    assert r.needs_escalation is True
    assert r.existing_appointment is True


def test_human_request_escalates():
    r = apply_rules("Can I talk to a human please")
    assert r.needs_escalation is True


def test_human_please_standalone_escalates():
    # Short form; must be detected as a human-handoff request.
    r = apply_rules("human please")
    assert r.needs_escalation is True
    assert r.escalation_reason.startswith("human_request:")


def test_need_a_human_escalates():
    r = apply_rules("I need a human")
    assert r.needs_escalation is True


def test_get_a_manager_escalates():
    r = apply_rules("can I get a manager")
    assert r.needs_escalation is True


def test_medical_spec_keywords_all_escalate():
    # Keywords the product spec says MUST escalate.
    for word in ("swelling", "reaction", "pain", "infection", "burn", "complication"):
        r = apply_rules(f"I have {word} at the injection site")
        assert r.needs_escalation is True, f"{word!r} did not escalate"


def test_reschedule_and_cancel_appointment_escalate():
    assert apply_rules("Can I reschedule?").needs_escalation is True
    assert apply_rules("I need to cancel my appointment").needs_escalation is True


def test_urgent_without_escalation():
    r = apply_rules("Need something asap")
    assert r.needs_escalation is False
    assert r.urgent is True


def test_normal_message_no_escalation():
    r = apply_rules("How much is Botox?")
    assert r.needs_escalation is False
    assert r.opt_out is False
