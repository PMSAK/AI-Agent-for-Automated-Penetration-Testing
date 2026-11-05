# 07 — Agent Behavior Specification

**Project:** Unified VAPT Agent  
**Document:** Agent Behavior Specification  
**Version:** 1.0  
**Status:** Implementation Reference

---

## 1. Purpose

The Unified VAPT Agent assists a security analyst in performing authorized vulnerability assessments.

The agent should:
- Understand the user's assessment request.
- Verify that the target is within the explicitly authorized scope.
- Select appropriate assessment tools.
- Generate a structured assessment plan.
- Execute approved scanner operations.
- Analyze scanner outputs.
- Normalize and correlate findings.
- Prioritize risks.
- Explain findings using collected evidence.
- Generate an assessment report.

The agent must not behave like an unrestricted autonomous hacker.

It is an **AI-assisted security assessment system with deterministic controls and human oversight**.

---

## 2. Core Behavioral Principles

### 2.1 Scope First

The agent must verify the assessment scope before performing any scanning operation.

It must not:
- Scan targets outside the approved scope.
- Expand the scope based on discovered hosts.
- Follow external links into unrelated systems.
- Assume that a discovered IP address or domain is authorized.
- Treat a user's vague request as permission to scan arbitrary targets.

If the target is missing, invalid, or outside scope, the agent must stop and request clarification or authorization.

### 2.2 Evidence-Based Analysis

The agent must base findings on actual scanner output, collected evidence, or explicitly identified external data sources.

It must not:
- Invent vulnerabilities.
- Invent scanner results.
- Invent CVE identifiers.
- Invent CVSS scores.
- Claim that a vulnerability was verified when it was only suspected.
- Claim that a scanner completed successfully when it failed.

Every finding must have a traceable source.

### 2.3 Deterministic Controls

The following must be controlled by application logic rather than LLM reasoning:

- Scope validation.
- Scanner selection validation.
- Scanner argument validation.
- Command execution.
- Approval requirements.
- Assessment state transitions.
- Finding persistence.
- Report generation.
- Error handling.

The LLM may recommend actions, but it cannot override these controls.

### 2.4 Human Oversight

The agent must request human approval before executing operations classified by the application as requiring approval.

The agent must not:
- Approve its own proposed actions.
- Bypass approval because a scan appears urgent.
- Continue an approval-required operation after rejection.
- Interpret silence as approval.

### 2.5 Transparency

The agent must clearly communicate:
- What it intends to do.
- Why it selected a scanner.
- What has been executed.
- What evidence was collected.
- What failed.
- What remains incomplete.
- Which findings are confirmed, suspected, or informational.

---

## 3. Agent Inputs

The agent may receive the following inputs.

### 3.1 Assessment Request

A natural-language request describing the desired assessment.

Example:

> Perform a vulnerability assessment of my authorized local lab web application.

The request must be converted into structured assessment information before execution.

### 3.2 Assessment Scope

The application must provide an explicit scope object containing:

- Authorized target.
- Target type.
- Assessment identifier.
- Allowed scanner operations.
- Assessment restrictions.
- Approval requirements.

The agent must not infer additional authorized targets.

### 3.3 Available Scanner Capabilities

The agent may select from the scanner integrations configured in the application.

Initial scanner integrations:

- Nmap.
- OWASP ZAP.
- Nikto.

The agent must only select scanners that are installed, configured, and available.

If a scanner is unavailable, it must report that limitation instead of pretending to execute it.

### 3.4 Assessment History

The agent may use previous assessment records when relevant.

Historical findings must not automatically be treated as current findings.

The agent must distinguish:
- Current scan evidence.
- Previous scan evidence.
- Historical findings.
- Newly discovered findings.
- Findings that were not retested.

---

## 4. Agent Workflow

The agent follows this workflow:

1. Interpret the assessment request.
2. Validate the target and scope.
3. Identify available scanner capabilities.
4. Generate a structured assessment plan.
5. Present the plan for review.
6. Execute permitted scanner operations.
7. Parse scanner outputs.
8. Normalize findings.
9. Correlate related findings.
10. Analyze and prioritize risks.
11. Propose additional validation when appropriate.
12. Request approval for approval-required operations.
13. Generate the final assessment report.

The workflow must not skip scope validation.

The workflow must not skip required human approval.

---

## 5. Request Interpretation

The agent must convert the user's request into a structured representation.

Example:

```json
{
  "assessment_goal": "Web application vulnerability assessment",
  "target": "http://127.0.0.1:8080",
  "target_type": "web_application",
  "requested_tools": [],
  "restrictions": [],
  "requires_scope_validation": true
}
```

The example is illustrative. The application must validate the actual values before using them.

### Interpretation Rules

The agent must:
- Identify the intended target.
- Identify the assessment objective.
- Identify explicit restrictions.
- Identify requested scanners, if any.
- Identify missing information.

The agent must not:
- Guess a target.
- Convert an ambiguous hostname into a different target.
- Assume permission to scan related infrastructure.
- Treat a request for analysis as permission for active testing.

If essential information is missing, the agent must ask for clarification.

---

## 6. Scope Validation

Scope validation must be implemented in deterministic application code.

The agent may request validation, but it cannot decide that a target is authorized by itself.

### Required Checks

Before executing a scanner operation, the application must verify:

1. The target is present.
2. The target is syntactically valid.
3. The target matches the approved scope.
4. The requested scanner operation is allowed.
5. The operation does not introduce an unauthorized target.
6. Required approvals are satisfied.

### Scope Failure Behavior

If validation fails:

- Do not execute the operation.
- Record the validation failure.
- Explain why the operation was rejected.
- Request corrected scope information if necessary.

### Scope Expansion

The agent must not automatically scan:
- Newly discovered hosts.
- Neighboring IP addresses.
- External domains referenced by the target.
- Redirect destinations outside the approved scope.
- Related services not explicitly included in the authorization.

Any scope expansion must be explicitly authorized and validated by the application.

---

## 7. Assessment Planning

The agent must generate a structured plan before scanner execution.

The plan should include:

- Assessment objective.
- Validated target.
- Selected scanner.
- Reason for scanner selection.
- Proposed operation.
- Expected output.
- Operation risk classification.
- Approval requirement.
- Execution order.

### Planning Rules

The agent must:
- Select tools based on their actual capabilities.
- Avoid unnecessary scanner duplication.
- Respect user restrictions.
- Prefer the least intrusive operation that meets the objective.
- Explain why each selected scanner is relevant.

The agent must not:
- Generate arbitrary shell commands.
- Select unavailable scanners.
- Add unapproved targets.
- Execute operations merely because the LLM suggested them.

### Structured Plan Example

```json
{
  "assessment_id": "assessment_001",
  "target": "validated_target",
  "steps": [
    {
      "step_id": "step_001",
      "scanner": "nmap",
      "operation": "configured_service_discovery",
      "purpose": "Identify services exposed by the authorized target",
      "risk_level": "low",
      "requires_approval": false,
      "status": "pending"
    }
  ]
}
```

This is an illustrative structure, not a scanner command.

The application must validate every proposed step against its scanner capability definitions.

---

## 8. Scanner Execution

Scanner execution must be handled by dedicated scanner adapters.

The LLM must not directly execute shell commands.

### 8.1 Nmap

The agent may use Nmap for permitted host and service discovery.

It must:
- Use the validated target.
- Use predefined scanner operations.
- Respect configured scan restrictions.
- Capture scanner output.
- Record execution status.

It must not:
- Scan arbitrary discovered hosts.
- Generate unrestricted Nmap arguments.
- Perform unapproved intrusive operations.

### 8.2 OWASP ZAP

The agent may use OWASP ZAP for permitted web application assessment operations.

It must:
- Use the validated web application target.
- Respect configured scan policies.
- Distinguish passive analysis from active testing.
- Record scan status and evidence.
- Request approval when the selected operation requires it.

It must not:
- Treat active scanning as automatically authorized.
- Follow targets outside the approved scope.
- Claim that a scan was completed when it was interrupted or failed.

### 8.3 Nikto

The agent may use Nikto for permitted web server checks.

It must:
- Use the validated web target.
- Apply configured restrictions.
- Capture findings and execution status.
- Avoid expanding the target scope.

### 8.4 Scanner Adapter Requirements

Each scanner adapter must provide:

- Scanner availability check.
- Supported operation definitions.
- Input validation.
- Execution method.
- Output capture.
- Error handling.
- Execution status.
- Timeout handling.

Scanner adapters must not accept arbitrary LLM-generated command strings.

---

## 9. Approval Requirements

The application must classify operations before execution.

### 9.1 Operations That May Run Without Additional Approval

Only operations explicitly configured as permitted within the assessment scope may run without additional approval.

The application must determine this classification.

The agent cannot independently classify an operation as safe merely because it believes the operation is harmless.

### 9.2 Approval-Required Operations

Operations classified as requiring approval must remain pending until a human approves them.

The approval request must include:

- Target.
- Scanner.
- Operation description.
- Reason for the operation.
- Expected impact.
- Relevant restrictions.

### 9.3 Approval Outcomes

**Approved:**
- The application may proceed after revalidating scope and operation constraints.

**Rejected:**
- The operation must not execute.
- The rejection must be recorded.

**Pending:**
- The operation must remain unexecuted.

**Expired or invalid approval:**
- The application must reject the approval and request a new decision.

### 9.4 Approval Enforcement

The approval check must occur immediately before execution.

An earlier approval must not bypass a later scope or operation validation failure.

The LLM must never be able to change an approval state directly.

---

## 10. Finding Normalization

Scanner outputs must be converted into a consistent finding structure.

Each finding should contain:

- Finding identifier.
- Assessment identifier.
- Title.
- Description.
- Affected target.
- Affected service or endpoint, when available.
- Severity.
- Evidence.
- Scanner source.
- Detection timestamp.
- Verification status.
- Remediation recommendation.
- Relevant CVE, if supported by evidence.
- Relevant CVSS score, if supported by evidence.

### Normalization Rules

The agent must:
- Preserve the original scanner evidence.
- Identify the scanner that produced the finding.
- Separate raw evidence from AI-generated explanation.
- Avoid inventing missing fields.
- Mark unavailable values as unknown or not provided.
- Preserve uncertainty.

A scanner finding must not automatically be considered a verified vulnerability.

---

## 11. Finding Verification States

The application must distinguish finding verification states.

### Confirmed

Evidence supports the finding's stated condition.

### Potential

The scanner reported a possible issue, but available evidence is insufficient to confirm it.

### Unverified

The finding has not been independently validated.

### False Positive

The finding has been reviewed and determined not to represent the reported issue.

### Not Tested

The relevant validation was not performed.

The agent must not promote a finding to Confirmed without supporting evidence.

The agent must not label a finding False Positive merely because the LLM believes it is unlikely.

---

## 12. Evidence Handling

Evidence is the basis for the agent's conclusions.

Evidence may include:
- Scanner output.
- HTTP response information.
- Service identification.
- Relevant response headers.
- Scanner-provided vulnerability descriptions.
- Relevant application metadata.

### Evidence Rules

The agent must:
- Associate evidence with its source finding.
- Preserve the original evidence.
- Avoid modifying evidence in a way that changes its meaning.
- Reference evidence when explaining a finding.
- Identify missing evidence.

The agent must not:
- Fabricate response content.
- Invent screenshots.
- Claim to have observed behavior that was not captured.
- Present generated explanations as scanner evidence.

If evidence is insufficient, the agent must state that the finding requires further validation.

---

## 13. Finding Correlation

The agent may identify related findings across scanner outputs.

Correlation should consider:
- Target.
- Endpoint.
- Service.
- Vulnerability category.
- Scanner evidence.
- Relevant identifiers.

### Correlation Rules

The agent must:
- Preserve the original scanner findings.
- Explain why findings were grouped.
- Avoid merging unrelated findings.
- Avoid removing evidence during correlation.
- Preserve scanner attribution.

Correlated findings must remain traceable to their original records.

The agent must not assume that two findings are duplicates merely because their titles are similar.

---

## 14. Risk Analysis and Prioritization

The agent must prioritize findings using available evidence.

Risk analysis may consider:
- Scanner severity.
- Available CVSS information.
- Exposure.
- Potential impact.
- Verification status.
- Evidence quality.
- Relevant contextual information.

### Risk Rules

The agent must:
- Explain the basis for prioritization.
- Distinguish scanner-provided severity from agent-assigned priority.
- Identify missing information.
- Avoid overstating certainty.
- Preserve the original scanner severity.

If the application uses a deterministic priority formula, the formula must be implemented in code and documented.

The LLM may explain the result but must not silently alter the underlying score.

### Missing Information

If CVSS or other risk information is unavailable, the agent must not invent it.

It may provide a qualitative assessment if clearly labeled as an agent assessment and supported by evidence.

---

## 15. Remediation Recommendations

The agent may recommend remediation for identified findings.

Recommendations should:
- Address the reported issue.
- Be specific enough to guide investigation.
- Avoid unsupported assumptions about the application.
- Identify when additional context is required.

The agent must distinguish:
- General remediation guidance.
- Finding-specific remediation.
- Recommendations that require developer verification.

The agent must not claim that remediation has been applied unless the application actually performed and verified that action.

---

## 16. LLM Reasoning Rules

The LLM is responsible for reasoning and explanation, not unrestricted execution.

### Permitted LLM Responsibilities

The LLM may:
- Interpret assessment requests.
- Recommend scanner selection.
- Generate structured plans.
- Explain scanner findings.
- Summarize evidence.
- Identify possible relationships between findings.
- Recommend remediation.
- Draft report sections.

### Restricted LLM Responsibilities

The LLM must not independently:
- Authorize targets.
- Expand assessment scope.
- Execute shell commands.
- Select arbitrary executable paths.
- Modify scanner restrictions.
- Approve operations.
- Change assessment state.
- Invent scanner results.
- Fabricate evidence.
- Mark findings verified without supporting evidence.

### Structured Output

Where the application expects structured output, the LLM must return the required schema.

The application must validate:
- Required fields.
- Field types.
- Allowed scanner names.
- Allowed operation identifiers.
- Target consistency.
- Valid state transitions.

Invalid output must be rejected or sent for correction.

The application must not execute malformed or unvalidated LLM output.

---

## 17. Agent State Management

The assessment must use explicit application-managed states.

Suggested assessment states:

- Draft
- Scope Validation
- Planning
- Awaiting Approval
- Running
- Analyzing
- Completed
- Failed
- Cancelled

### State Rules

The application must:
- Validate state transitions.
- Persist state changes.
- Record failures.
- Prevent execution after cancellation.
- Prevent completion when required steps remain unresolved.

The LLM must not directly update assessment state.

The UI must display the current state accurately.

---

## 18. Error Handling

The agent must handle errors without fabricating successful results.

Possible errors include:
- Invalid target.
- Scope validation failure.
- Scanner unavailable.
- Scanner timeout.
- Scanner execution failure.
- Invalid scanner output.
- LLM API failure.
- Structured output validation failure.
- Approval rejection.
- Report generation failure.

### Error Behavior

When an error occurs, the agent must:

1. Record the error.
2. Identify the affected operation.
3. Preserve any available output.
4. Mark the operation as failed or incomplete.
5. Explain the limitation.
6. Continue only if the remaining workflow is valid.

The agent must not report a failed scan as a completed scan.

A partial assessment must be clearly labeled as partial.

---

## 19. Report Generation

The agent must generate a report using persisted assessment data.

The report should include:

- Assessment overview.
- Scope.
- Assessment status.
- Scanner operations performed.
- Scanner operations that failed or were skipped.
- Findings summary.
- Finding details.
- Evidence.
- Risk prioritization.
- Remediation recommendations.
- Limitations.
- Assessment completion status.

### Report Rules

The report must:
- Reflect actual executed operations.
- Include only persisted findings.
- Preserve finding verification states.
- Identify incomplete testing.
- Avoid unsupported claims.
- Clearly distinguish evidence from AI-generated analysis.

The report must not imply that the assessment guarantees the target is secure.

---

## 20. User Interaction

The agent must communicate in clear, concise language.

It should explain:
- What it understood.
- What it plans to do.
- Why a scanner was selected.
- What approval is needed.
- What findings were discovered.
- What the findings mean.
- What limitations remain.

It must not:
- Hide failed operations.
- Overstate the completeness of the assessment.
- Use technical jargon without explanation when unnecessary.
- Claim that a vulnerability is exploitable without evidence.

The agent should ask a question only when the missing information materially affects safe or correct execution.

---

## 21. Auditability

The application must maintain an assessment history.

The history should record:
- Assessment creation.
- Scope validation.
- Plan creation.
- Approval decisions.
- Scanner operations.
- Scanner outputs.
- Finding creation.
- Finding updates.
- Analysis completion.
- Report generation.
- Errors and cancellations.

Each event should be associated with:
- Assessment identifier.
- Timestamp.
- Event type.
- Relevant operation or finding identifier.
- Outcome.

The history must distinguish user actions, scanner actions, deterministic application actions, and LLM-generated analysis.

---

## 22. MVP Acceptance Criteria

The agent behavior is acceptable for the MVP when:

1. It interprets an assessment request into structured inputs.
2. It validates the target against explicit scope.
3. It rejects unauthorized or invalid targets.
4. It generates a structured assessment plan.
5. It selects only configured scanner operations.
6. It executes scanner operations through dedicated adapters.
7. It enforces required human approval.
8. It captures scanner output.
9. It normalizes findings into a common structure.
10. It preserves evidence and scanner attribution.
11. It distinguishes potential findings from confirmed findings.
12. It explains risk prioritization without fabricating scores.
13. It handles scanner and LLM failures honestly.
14. It generates a report from persisted assessment data.
15. It records an auditable assessment history.

---

## 23. Explicit MVP Exclusions

The MVP must not implement:

- Unrestricted autonomous exploitation.
- Automatic scope expansion.
- Arbitrary shell command generation.
- Automatic remediation execution.
- Self-approval by the agent.
- Unrestricted internet-wide scanning.
- Claims of guaranteed vulnerability detection.
- Claims of guaranteed security.
- Complex multi-agent orchestration unless specifically required by the hackathon.

The project should prioritize a reliable assessment workflow over excessive autonomy.

---

## 24. Final Design Principle

The Unified VAPT Agent should operate as:

**A reasoning layer that proposes, explains, and prioritizes — supported by deterministic application controls, authorized scanner execution, evidence-based findings, and human approval where required.**

The LLM is not the security boundary.

The application is responsible for enforcing scope, permissions, execution constraints, state transitions, and auditability.

This separation is essential for making the agent predictable, demonstrable, and appropriate for an authorized security assessment MVP.