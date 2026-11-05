# AI-Powered Unified VAPT Agent
## 03 — Application Flow

**Version:** 1.0 — Initial workflow specification  
**Status:** Proposed  
**Related documents:** 01_PRD.md, 02_TRD.md

---

## 1. Purpose

This document defines the user-facing and system-level workflows for the AI-powered Unified VAPT Agent.

It describes how an analyst creates an assessment, validates its scope, reviews the agent's plan, executes approved scans, analyzes findings, reviews risks, approves active validation, and generates a final report.

The application flow must satisfy the mandatory requirements in the hackathon problem statement and the approved PRD.

---

## 2. Primary User

The primary user is a security analyst conducting an authorized assessment against an explicitly approved lab target.

The analyst is responsible for:

- Providing the authorized target.
- Defining assessment scope.
- Reviewing the assessment plan.
- Reviewing findings.
- Approving or rejecting active validation.
- Reviewing the final report.

The agent assists with assessment planning, tool selection, result interpretation, correlation, prioritization, and reporting.

---

## 3. Main Application Navigation

The application shall provide the following primary sections:

1. Dashboard
2. New Assessment
3. Assessment Details
4. Findings
5. Reports
6. Scanner Integrations

The exact visual layout will be specified in 04_UI_UX_DESIGN_BRIEF.md.

### 3.1 Dashboard

The dashboard shall display:

- Assessment summary.
- Recent assessments.
- Assessment status.
- Findings summary.
- Scanner execution status.
- Report availability.

The dashboard shall not display fabricated assessment metrics.

### 3.2 New Assessment

The analyst begins a new assessment by providing the target and authorized scope.

### 3.3 Assessment Details

The assessment details page shall display:

- Assessment request.
- Approved scope.
- Assessment plan.
- Scanner execution status.
- Findings.
- Approval history.
- Report status.

### 3.4 Findings

The findings section shall display normalized findings and allow the analyst to inspect supporting evidence.

### 3.5 Reports

The reports section shall provide access to generated assessment reports.

### 3.6 Scanner Integrations

The integrations section shall display the available scanner adapters and their current verification status.

---

## 4. Main Assessment Workflow

The primary workflow is:

Dashboard → New Assessment → Scope Validation → Assessment Plan → Analyst Review → Scan Execution → Result Processing → Finding Analysis → Risk Prioritization → Analyst Review → Approved Validation, if required → Report Generation → Completed Assessment

The system shall not execute scanner operations before scope validation.

The system shall not execute active exploitation or offensive validation without explicit human approval.

---

## 5. Detailed Workflow

### Step 1 — Create Assessment

**User action**

The analyst opens New Assessment and provides:

- Assessment name.
- Natural-language assessment request.
- Target host, IP address, or URL.
- Authorized scope.
- Excluded targets or paths, where applicable.
- Relevant assessment constraints.

**System action**

The application:

1. Validates required input fields.
2. Creates an assessment record.
3. Stores the original request.
4. Stores the submitted target and scope.
5. Sets the assessment status to `created`.

**Failure handling**

If required information is missing or invalid, the application shall identify the missing or invalid input and prevent progression.

The application shall not invent target information.

---

### Step 2 — Validate Assessment Scope

**User action**

The analyst reviews the submitted target and authorization boundaries.

**System action**

The scope validator:

1. Parses the target.
2. Validates its format.
3. Checks the target against the explicitly authorized scope.
4. Identifies exclusions.
5. Determines whether the requested assessment can proceed.
6. Records the validation outcome.

**Successful outcome**

The application records scope validation as successful and allows planning to continue.

**Failure outcome**

If the target is invalid, unauthorized, excluded, or ambiguous:

- The assessment shall not execute scans.
- The application shall explain why the target was rejected.
- The assessment shall remain in a blocked state until the scope is corrected.

**Safety requirement**

The LLM shall not override the scope validator.

---

### Step 3 — Generate Assessment Plan

**System action**

The agent analyzes:

- The assessment request.
- The validated target.
- Authorized scope.
- Available scanner capabilities.
- Existing assessment information, if available.

The agent generates a structured assessment plan.

The plan shall include:

- Assessment objectives.
- Selected tools.
- Intended scan operations.
- Reason for each tool selection.
- Expected output.
- Relevant prerequisites.
- Planned sequence.
- Potential limitations.

The agent shall explain why a subsequent investigation is needed when additional scanning is proposed.

The plan shall avoid unnecessary or repeated scans.

**User action**

The analyst reviews the plan.

The analyst may:

- Approve the plan.
- Reject the plan.
- Modify permitted assessment parameters.
- Return to scope configuration.

**Outcome**

The application records the plan and the analyst's decision.

Scan execution shall begin only after the plan has been accepted.

---

### Step 4 — Execute Approved Scans

**System action**

The scanner orchestrator executes the approved plan through predefined scanner adapters.

The initial planned adapters are:

- Nmap.
- OWASP ZAP.
- Nikto.

The orchestrator shall:

1. Verify that the assessment scope remains valid.
2. Verify scanner availability.
3. Validate scanner inputs.
4. Execute the approved scanner operation.
5. Track execution status.
6. Collect scanner output.
7. Record execution metadata.
8. Report failures or timeouts.

**User action**

The analyst monitors the assessment progress.

**Execution states**

- `queued`
- `running`
- `completed`
- `failed`
- `timed_out`
- `cancelled`

**Failure handling**

If a scanner fails:

- The failure shall be recorded.
- The application shall not fabricate results.
- The system may continue with other permitted independent scans.
- The analyst shall be informed of the failed operation.
- The final report shall disclose the failure.

The application shall not mark the entire assessment successful merely because one scanner completed.

---

### Step 5 — Collect and Parse Scanner Results

**System action**

The application collects scanner outputs and execution metadata.

Each result shall be associated with:

- Assessment.
- Scanner.
- Scanner version, when available.
- Execution identifier.
- Execution timestamps.
- Target.
- Original output reference.
- Execution status.

The parser converts supported scanner output into structured intermediate data.

The application shall preserve the original output or a traceable reference to it.

**Failure handling**

If a scanner output cannot be parsed:

- The original output shall remain available.
- The parsing failure shall be recorded.
- The application shall not silently discard the result.
- The analyst shall be informed.

---

### Step 6 — Normalize Findings

**System action**

The normalizer converts supported scanner findings into the common finding schema.

For each finding, the system shall preserve:

- Finding identifier.
- Assessment identifier.
- Title.
- Description.
- Affected asset.
- Severity.
- CVSS information, if available.
- CVE/CWE references, if applicable.
- Source scanner.
- Source finding identifier.
- Evidence references.
- Confidence.
- Validation status.
- Remediation information.
- Timestamps.

The application shall distinguish:

- Scanner-observed facts.
- AI-generated interpretation.
- Unknown or missing information.

The application shall not fabricate missing fields.

---

### Step 7 — Correlate and Deduplicate Findings

**System action**

The correlation component compares findings from different scanners.

It considers:

- Affected asset.
- Finding category.
- Endpoint or service.
- Vulnerability identity.
- Supporting evidence.
- Scanner-native identifiers.

The system shall identify potential duplicates and merge genuine duplicates where appropriate.

Merged findings shall preserve:

- Original scanner references.
- Evidence from each contributing scanner.
- Distinct affected assets.
- Original severity values.
- Correlation rationale.

The system shall not merge findings solely because their titles or descriptions are similar.

**Failure handling**

If correlation is uncertain, findings shall remain separate or be marked as potential duplicates for analyst review.

---

### Step 8 — Analyze Findings and Prioritize Risks

**System action**

The agent analyzes normalized findings using available:

- Severity/CVSS.
- Exposure.
- Exploitability.
- Asset impact.
- Confidence.
- Supporting evidence.

The system shall produce:

- Finding summaries.
- Risk explanations.
- Prioritized findings.
- Remediation recommendations.
- Confidence information.
- Evidence references.

The system shall not invent CVEs, exploit evidence, CVSS values, or validation outcomes.

**User action**

The analyst reviews the prioritized findings.

The analyst may inspect:

- Finding details.
- Affected assets.
- Evidence.
- Source scanner.
- Confidence.
- Risk explanation.
- Remediation recommendation.

---

### Step 9 — Request Active Validation

Active validation is not automatically required for every finding.

When the agent proposes active validation, it shall generate a structured proposal.

The proposal shall include:

- Finding identifier.
- Target asset.
- Proposed validation action.
- Purpose.
- Expected evidence.
- Potential impact.
- Scope constraints.
- Reason for validation.

The application shall display the proposal to the analyst.

**Required user actions**

The analyst may:

- Approve.
- Reject.
- Defer.

**Approval requirement**

Explicit human approval is mandatory before active exploitation or offensive validation.

The LLM shall not approve its own proposed action.

The application shall record:

- Proposed action.
- Assessment.
- Finding.
- Analyst decision.
- Decision timestamp.
- Approval status.
- Execution outcome, if approved.

**Rejected proposal**

If rejected:

- The proposed validation shall not execute.
- The rejection shall be recorded.
- The finding shall remain available.
- The report shall reflect its existing validation status.

**Deferred proposal**

If deferred:

- The action shall remain unexecuted.
- The application shall preserve the pending decision.
- The assessment may continue with other permitted operations.

---

### Step 10 — Generate Assessment Report

**User action**

The analyst selects Generate Report.

**System action**

The report generator retrieves assessment data and creates the PDF.

The report shall include:

1. Executive summary.
2. Assessment scope.
3. Methodology.
4. Scanner execution summary.
5. Severity distribution.
6. Detailed findings.
7. Supporting evidence.
8. Risk explanations.
9. Remediation recommendations.
10. Assessment limitations.
11. Scanner failures.
12. Approval records.
13. Assessment timestamps.

The report shall use persisted assessment data.

The LLM shall not independently invent report findings.

**Failure handling**

If report generation fails:

- The application shall record the failure.
- The assessment data shall remain available.
- The application shall not claim that the report was generated.
- The analyst shall be able to retry.

---

### Step 11 — Complete Assessment

An assessment may be marked completed when:

- Scope validation succeeded.
- The accepted assessment plan has been processed.
- Scanner execution outcomes have been recorded.
- Available results have been processed.
- Findings have been persisted.
- Required approval decisions have been recorded.
- The report has been generated, or the application explicitly records why it could not be generated.

The application shall distinguish:

- Completed assessment.
- Completed with limitations.
- Failed assessment.
- Cancelled assessment.

A completed assessment shall not imply that every scanner succeeded or that every finding was validated.

---

## 6. Assessment State Model

The proposed assessment states are:

| State | Meaning |
|---|---|
| `created` | Assessment record exists |
| `scope_pending` | Scope validation has not completed |
| `scope_rejected` | Scope validation failed |
| `planning` | Agent is generating a plan |
| `plan_pending_review` | Plan awaits analyst decision |
| `plan_rejected` | Analyst rejected the plan |
| `ready` | Plan accepted and execution may begin |
| `running` | Approved scanner operations are executing |
| `processing_results` | Results are being parsed and normalized |
| `review_pending` | Findings await analyst review |
| `approval_pending` | Active validation awaits analyst decision |
| `reporting` | PDF report is being generated |
| `completed` | Assessment processing and report generation completed |
| `completed_with_limitations` | Assessment completed with recorded limitations |
| `failed` | Assessment could not complete |
| `cancelled` | Assessment was cancelled |

The implementation shall define valid state transitions.

The application shall prevent invalid transitions, such as starting a scan after scope rejection or executing active validation while approval is pending.

---

## 7. Scanner Execution State Model

Each scanner execution shall have an independent status.

| State | Meaning |
|---|---|
| `queued` | Awaiting execution |
| `running` | Scanner is executing |
| `completed` | Scanner completed successfully |
| `failed` | Scanner execution failed |
| `timed_out` | Scanner exceeded its allowed execution time |
| `cancelled` | Scanner execution was cancelled |

An assessment may contain multiple scanner executions with different outcomes.

The application shall preserve the status of each individual execution.

---

## 8. Approval State Model

Each active validation proposal shall have an independent approval status.

| State | Meaning |
|---|---|
| `pending` | Awaiting analyst decision |
| `approved` | Analyst explicitly approved |
| `rejected` | Analyst rejected |
| `deferred` | Analyst postponed the decision |
| `executed` | Approved action completed |
| `execution_failed` | Approved action failed |
| `cancelled` | Proposal was cancelled |

Approval and execution shall be separate events.

An approved action shall not be marked executed until its execution outcome has been recorded.

---

## 9. Important Alternative Flows

### 9.1 Invalid Target

If the target format is invalid:

1. Display the validation error.
2. Do not execute scans.
3. Allow the analyst to correct the target.

### 9.2 Unauthorized Target

If the target is outside the authorized scope:

1. Reject the requested operation.
2. Record the rejection.
3. Explain the scope violation.
4. Do not execute scans.

### 9.3 Scanner Unavailable

If a scanner is unavailable:

1. Record the scanner status.
2. Mark the execution as failed or unavailable.
3. Continue only with permitted independent scanner operations.
4. Disclose the limitation.

### 9.4 Scanner Timeout

If a scanner times out:

1. Stop or terminate the scanner operation according to its adapter contract.
2. Record the timeout.
3. Preserve available output.
4. Do not treat the execution as successful.

### 9.5 No Findings

If a completed scan produces no findings:

1. Record the successful execution.
2. Report that no findings were returned by that scanner.
3. Avoid claiming that the target is secure.
4. Preserve the scan scope and limitations.

### 9.6 Malformed Scanner Output

If output parsing fails:

1. Preserve the original output.
2. Record the parser error.
3. Do not create fabricated normalized findings.
4. Allow analyst review.

### 9.7 Uncertain Duplicate

If two findings may be duplicates but correlation is uncertain:

1. Preserve both findings.
2. Mark the correlation as uncertain.
3. Provide supporting information for review.

### 9.8 Missing Evidence

If evidence is unavailable:

1. Mark evidence as missing.
2. Reduce or qualify confidence where appropriate.
3. Do not invent evidence.
4. Disclose the limitation.

### 9.9 Validation Rejected

If the analyst rejects active validation:

1. Do not execute the proposed action.
2. Record the rejection.
3. Preserve the finding.
4. Continue with permitted assessment operations.

### 9.10 Report Generation Failure

If PDF generation fails:

1. Record the failure.
2. Preserve assessment data.
3. Display the error.
4. Allow report generation to be retried.

---

## 10. Audit Trail

The application shall record significant assessment events.

The audit trail shall include:

- Assessment creation.
- Scope validation.
- Scope rejection.
- Plan generation.
- Plan acceptance or rejection.
- Scanner execution start.
- Scanner execution completion.
- Scanner failure.
- Result ingestion.
- Finding normalization.
- Finding correlation.
- Approval proposal.
- Approval decision.
- Validation execution.
- Report generation.
- Report generation failure.
- Assessment completion.

Each event shall include an assessment reference and timestamp.

Where applicable, events shall include the responsible user, scanner, finding, and execution references.

The audit trail shall not contain API keys or unnecessary sensitive information.

---

## 11. MVP User Journey

The primary demonstration shall follow this journey:

1. Analyst opens the dashboard.
2. Analyst creates a new assessment.
3. Analyst enters an authorized lab target and scope.
4. Application validates the scope.
5. Agent generates an assessment plan.
6. Analyst reviews and accepts the plan.
7. Application executes approved scanner integrations.
8. Application records scanner execution outcomes.
9. Application parses and normalizes results.
10. Agent analyzes findings and proposes risk priorities.
11. Analyst reviews evidence-backed findings.
12. Agent proposes active validation only where appropriate.
13. Analyst approves or rejects the proposed validation.
14. Application records the decision and any execution outcome.
15. Analyst generates the PDF report.
16. Analyst downloads and reviews the report.

The demonstration shall disclose scanner failures and unsupported integrations.

---

## 12. Workflow Acceptance Criteria

The application flow is acceptable when:

- Invalid targets cannot proceed to scanning.
- Unauthorized targets cannot proceed to scanning.
- The agent produces a structured assessment plan.
- The analyst can review the plan before execution.
- Scanner operations are tracked individually.
- Scanner failures and timeouts are recorded.
- Scanner outputs are preserved.
- Findings are normalized.
- Duplicate handling preserves distinct assets and evidence.
- Risk prioritization is supported.
- Active validation requires explicit approval.
- Approval decisions and outcomes are recorded.
- Reports disclose limitations.
- Report findings are traceable to source evidence.
- Assessment completion accurately reflects execution outcomes.

---

## 13. Relationship to Other Documents

This document defines application behavior and state transitions.

The remaining documents shall specify:

- 04_UI_UX_DESIGN_BRIEF.md — interface presentation.
- 05_BACKEND_SCHEMA.md — persistence structures.
- 06_IMPLEMENTATION_PLAN.md — development sequence.
- 07_AGENT_BEHAVIOR.md — agent planning and reasoning.
- 08_TOOL_CONTRACTS.md — scanner execution contracts.
- 09_SAFETY_RULES.md — safety enforcement.

Any conflicting workflow or state definition shall be resolved before implementation.
