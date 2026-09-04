"""Deterministic MDR (21 CFR 803) reportability decision engine.

Pure, rule-based Python — no ML/LLM call anywhere in this module. Evaluates
the six rules below in strict order and stops at the first one that matches,
exactly as specified. Every branch records which rule fired, which field
values drove it, and what regulatory standard was applied, so the resulting
`mdr_reasoning` text can stand on its own if read aloud to an FDA inspector.

Rule order (first match wins):
  1. Death caused/contributed by the device               -> Reportable
  2. Serious injury caused/contributed by the device       -> Reportable
  3. Dangerous malfunction, independent of injury outcome  -> Reportable
  4. A field rules 1-3 would need to decide is Unknown     -> Needs Human Review
  5. Known serious injury/death, but causality "Unrelated" -> Needs Human Review
  6. Neither threshold met                                 -> Not Reportable

Deadline modifier (applies to any Reportable result): remedial action taken
-> 5 working days; otherwise -> 30 calendar days, both computed from
date_received.
"""

from datetime import date, timedelta

SERIOUS_INJURY_DEFINITION = (
    "A serious injury is one that is life-threatening, results in permanent "
    "impairment of a body function or permanent damage to a body structure, "
    "or necessitates medical or surgical intervention to preclude permanent "
    "impairment or damage."
)

REPORTABLE = "Reportable"
NOT_REPORTABLE = "Not Reportable"
NEEDS_REVIEW = "Needs Human Review"

_CAUSALITY_POSITIVE = {"Caused", "Contributed"}


def _add_working_days(start: date, n: int) -> date:
    d = start
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Mon=0 .. Fri=4; skip Sat/Sun
            added += 1
    return d


def _deadline(date_received: date, remedial_action_taken: bool):
    if remedial_action_taken:
        due = _add_working_days(date_received, 5)
        note = (
            "Remedial action was taken to reduce a risk to health, so the "
            "expedited 5-working-day deadline applies rather than the "
            f"standard 30 days. Due date: {due.isoformat()}, computed as 5 "
            "working days from date_received with Saturdays and Sundays "
            "excluded. Note: this calculation does NOT account for federal "
            "holidays — if one falls within the window, the true regulatory "
            "deadline is earlier than the date shown here and should be "
            "confirmed manually."
        )
        return 5, due, note
    due = date_received + timedelta(days=30)
    note = (
        "No remedial action was taken, so the standard 30-calendar-day "
        f"deadline applies. Due date: {due.isoformat()}, computed as 30 "
        "calendar days from date_received."
    )
    return 30, due, note


def evaluate_mdr(
    *,
    injury_severity: str,
    device_causality: str,
    device_malfunctioned: str,
    recurrence_would_be_dangerous: str,
    remedial_action_taken: bool,
    date_received: date,
) -> dict:
    severity_known = injury_severity != "Unknown"
    causality_known = device_causality != "Unknown"
    malfunction_known = device_malfunctioned != "Unknown"
    recurrence_known = recurrence_would_be_dangerous != "Unknown"

    is_death = injury_severity == "Death"
    is_serious = injury_severity == "Serious"
    causality_positive = device_causality in _CAUSALITY_POSITIVE
    causality_unrelated = device_causality == "Unrelated"
    malfunction_yes = device_malfunctioned == "Yes"
    recurrence_yes = recurrence_would_be_dangerous == "Yes"
    recurrence_no = recurrence_would_be_dangerous == "No"

    # ---- Rule 1: Death caused/contributed by the device ----
    if severity_known and is_death and causality_known and causality_positive:
        deadline_days, due_date, deadline_note = _deadline(date_received, remedial_action_taken)
        reasoning = (
            "REPORTABLE — Rule 1 (Death). injury_severity is 'Death' and "
            f"device_causality is '{device_causality}', meaning the device "
            "caused or contributed to the death. Under 21 CFR 803.50, a "
            "death where the device caused or contributed requires an MDR "
            "to FDA. " + deadline_note
        )
        return {
            "mdr_decision": REPORTABLE,
            "mdr_deadline_days": deadline_days,
            "mdr_due_date": due_date,
            "mdr_reasoning": reasoning,
        }

    # ---- Rule 2: Serious injury caused/contributed by the device ----
    if severity_known and is_serious and causality_known and causality_positive:
        deadline_days, due_date, deadline_note = _deadline(date_received, remedial_action_taken)
        reasoning = (
            "REPORTABLE — Rule 2 (Serious injury). injury_severity is "
            f"'Serious' and device_causality is '{device_causality}', "
            "meaning the device caused or contributed to a serious injury "
            f"as legally defined: {SERIOUS_INJURY_DEFINITION} Under 21 CFR "
            "803.50, this requires an MDR to FDA. " + deadline_note
        )
        return {
            "mdr_decision": REPORTABLE,
            "mdr_deadline_days": deadline_days,
            "mdr_due_date": due_date,
            "mdr_reasoning": reasoning,
        }

    # ---- Rule 3: dangerous malfunction, independent of injury outcome ----
    if malfunction_known and malfunction_yes and recurrence_known and recurrence_yes:
        deadline_days, due_date, deadline_note = _deadline(date_received, remedial_action_taken)
        reasoning = (
            "REPORTABLE — Rule 3 (dangerous malfunction, no injury "
            "required). device_malfunctioned is 'Yes' and "
            "recurrence_would_be_dangerous is 'Yes': were this malfunction "
            "to recur, it would be reasonably likely to cause or contribute "
            "to a death or serious injury. Per 21 CFR 803.50, this makes "
            "the event reportable regardless of whether an injury actually "
            "occurred this time — the standard is the malfunction's "
            "potential on recurrence, not the outcome of this single "
            "incident. " + deadline_note
        )
        return {
            "mdr_decision": REPORTABLE,
            "mdr_deadline_days": deadline_days,
            "mdr_due_date": due_date,
            "mdr_reasoning": reasoning,
        }

    # ---- Rule 4: a field rules 1-3 would need is Unknown ----
    missing = []  # list of (field_name, explanation)

    if not severity_known:
        # Unknown severity blocks everything downstream: rules 1/2/5 need it
        # known Serious/Death, and rule 6 needs it confirmed NOT Serious/
        # Death. Only rule 3 doesn't depend on it, and we've already ruled
        # that out above.
        missing.append((
            "injury_severity",
            "if this turns out to be Serious or Death together with a "
            "device_causality of Caused or Contributed, Rule 1/2 would make "
            "this Reportable (30 days); if it turns out to be None or "
            "Minor, this would likely be Not Reportable. Needs the "
            "clinical record or a follow-up with the complainant/treating "
            "provider to establish the actual outcome.",
        ))
    elif is_death or is_serious:
        if not causality_known:
            missing.append((
                "device_causality",
                f"injury_severity is confirmed '{injury_severity}', but "
                "whether the device caused or contributed to it, versus "
                "being unrelated, is not yet established. This single fact "
                "determines whether this is Reportable (Rule 1/2) or "
                "requires a documented causality review (Rule 5). Needs a "
                "clinical/causality assessment, typically from the "
                "treating physician's records or a Meridian Spine medical "
                "reviewer.",
            ))
        # If causality is known and "Unrelated", that's not a missing-
        # information case — Rule 5 handles it explicitly below. If
        # causality is known and positive, Rule 1/2 already matched above.

    if malfunction_known and malfunction_yes:
        if not recurrence_known:
            missing.append((
                "recurrence_would_be_dangerous",
                "device_malfunctioned is confirmed 'Yes', but whether a "
                "recurrence of this same malfunction would be reasonably "
                "likely to cause or contribute to death or serious injury "
                "has not been assessed. This determines whether Rule 3 "
                "makes this Reportable independent of any injury this "
                "time. Needs an engineering/failure-analysis risk "
                "assessment of the malfunction mode.",
            ))
    elif not malfunction_known:
        if not (recurrence_known and recurrence_no):
            # recurrence is Yes or Unknown — can't rule out Rule 3 without
            # first knowing whether a malfunction actually occurred.
            missing.append((
                "device_malfunctioned",
                "whether the device actually malfunctioned has not been "
                "established. If it did, and a recurrence would plausibly "
                "be dangerous, Rule 3 would make this Reportable regardless "
                "of this incident's injury outcome. Needs the returned "
                "unit (if available) sent for failure analysis, or an "
                "engineering review of the reported event.",
            ))
            if not recurrence_known:
                missing.append((
                    "recurrence_would_be_dangerous",
                    "in addition to whether a malfunction occurred at all, "
                    "whether a recurrence would be dangerous is also not "
                    "established. Needs an engineering risk assessment.",
                ))
    # If device_malfunctioned is known "No", Rule 3 cannot fire regardless
    # of recurrence_would_be_dangerous, so there's nothing to add here.

    if missing:
        field_lines = "; ".join(f"{name} — {why}" for name, why in missing)
        reasoning = (
            "NEEDS HUMAN REVIEW — Rule 4 (unknowns block a decision). "
            "The facts on file do not permit a confident reportability "
            "determination under 21 CFR 803.50's 'reasonably suggests' "
            "standard. 'Unknown' is not being treated as 'No', and no "
            "value is being guessed. Missing/undetermined field(s): "
            f"{field_lines}"
        )
        return {
            "mdr_decision": NEEDS_REVIEW,
            "mdr_deadline_days": None,
            "mdr_due_date": None,
            "mdr_reasoning": reasoning,
        }

    # ---- Rule 5: known serious injury/death, but causality "Unrelated" ----
    if severity_known and (is_death or is_serious) and causality_known and causality_unrelated:
        reasoning = (
            "NEEDS HUMAN REVIEW — Rule 5 (causality unresolved despite "
            f"known harm). injury_severity is confirmed '{injury_severity}', "
            "but device_causality is recorded as 'Unrelated'. A "
            "determination that a serious injury or death is unrelated to "
            "the device is itself a judgment call that carries real "
            "regulatory risk if incorrect, so it is not treated as "
            "automatic Not Reportable. A Quality/Regulatory reviewer must "
            "independently confirm the 'Unrelated' causality assessment "
            "(e.g. against clinical records, or device return/failure "
            "analysis if the unit is available) before Meridian Spine "
            f"declines to report this {'death' if is_death else 'serious injury'}."
        )
        return {
            "mdr_decision": NEEDS_REVIEW,
            "mdr_deadline_days": None,
            "mdr_due_date": None,
            "mdr_reasoning": reasoning,
        }

    # ---- Rule 6: neither threshold met ----
    # By this point injury_severity is known and is not Death/Serious
    # (otherwise Rule 5 or the causality branch of Rule 4 would have caught
    # it), and at least one of device_malfunctioned / recurrence_would_be_
    # dangerous is confirmed "No" (otherwise Rule 3 would already have
    # fired, or Rule 4 would have caught the remaining ambiguity).
    checked = []
    if device_malfunctioned == "No":
        checked.append("device_malfunctioned is 'No'")
    if recurrence_would_be_dangerous == "No":
        checked.append("recurrence_would_be_dangerous is 'No'")
    checked_str = " and ".join(checked) if checked else "the malfunction/recurrence criteria are not met"

    reasoning = (
        "NOT REPORTABLE — Rule 6. Checked: injury_severity is "
        f"'{injury_severity}' (not Serious or Death), and {checked_str}. "
        "Neither the death/serious-injury threshold (Rule 1/2) nor the "
        "dangerous-malfunction-on-recurrence threshold (Rule 3) is met, so "
        "under 21 CFR 803.50 this complaint does not currently meet the "
        "criteria for an MDR report. If any of these facts change (e.g. "
        "the patient's condition worsens, or failure analysis later shows "
        "a malfunction with dangerous recurrence potential), this "
        "complaint should be re-evaluated."
    )
    return {
        "mdr_decision": NOT_REPORTABLE,
        "mdr_deadline_days": None,
        "mdr_due_date": None,
        "mdr_reasoning": reasoning,
    }
