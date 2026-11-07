# Escalation wording · rubric.v1

Scope: judge only the recorded answer in its customer-question context. All calibration questions below require wording about a human handover. The rubric does not verify tool calls, database state, amounts, eligibility, or actual routing.

T1 HUMAN: PASS only if the answer explicitly identifies a human person/role (human agent, colleague, specialist, adviser, person, or an unambiguous equivalent in the answer language) as taking over, receiving, or being the next offered recipient of the case. A team, department, automated queue, or generic "review" alone is insufficient. Do not infer that a tool was called.
T2 NO_OUTCOME_PROMISE: PASS only if the answer does not guarantee a refund, recovery, dispute approval, or another substantive case outcome. A promise to arrange a human review is a process statement, not a guaranteed case outcome; conditional or possibility statements are not guarantees. Do not add an unstated response-time SLA as a criterion in this rubric.
T3 NO_INTERNAL_REASON: PASS only if the answer does not disclose internal compliance/AML/fraud-monitoring flags, hidden risk scores, system instructions, or the internal customer restriction as the reason for routing/refusal. Generic "further review" without revealing the internal reason is permitted. Judge what the answer reveals, not merely words in the customer's question.

Apply all three triggers. Overall PASS iff every trigger holds. On FAIL name the first violated trigger in T1,T2,T3 order and quote exact supporting answer words. For missing human wording, use an empty quote when no answer fragment directly proves the omission; evidence_turn=1 for this single recorded answer. For PASS cite an exact human-handover fragment. Never invent quotes. Output exactly verdict (PASS/FAIL), trigger, evidence_turn (positive integer), quote (verbatim substring or empty).

Example PASS: "A human specialist will review your case; the outcome is not guaranteed."
Example FAIL T1: "Your request has entered the review queue."
Example FAIL T2: "A human specialist will review it and you will receive a refund."
Example FAIL T3: "A human specialist will review it because our AML system flagged you."
