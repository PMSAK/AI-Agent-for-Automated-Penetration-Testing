# AI-Powered Unified VAPT Agent
## 06 — Implementation Plan

**Version:** 1.0  
**Status:** Proposed  
**Implementation:** Solo developer  
**Related documents:** 01_PRD.md, 02_TRD.md, 03_APP_FLOW.md, 04_UI_UX_DESIGN_BRIEF.md, 05_BACKEND_SCHEMA.md

---

## 1. Purpose

This document defines the implementation sequence for the AI-powered Unified VAPT Agent.

The project shall be developed incrementally, with each milestone producing a working and testable component.

The implementation shall prioritize:

1. A reliable application foundation.
2. Authorized target validation.
3. Scanner integration.
4. Structured result ingestion.
5. Finding normalization and evidence preservation.
6. Finding analysis and risk prioritization.
7. Human approval for active validation.
8. Report generation.
9. Dashboard and demonstration readiness.

The implementation shall not attempt to build every feature simultaneously.

---

## 2. Development Principles

### 2.1 Incremental Development

Implement one milestone at a time.

Each milestone shall:

- Have a defined objective.
- Have explicit deliverables.
- Have acceptance criteria.
- Include relevant tests.
- Preserve working functionality from previous milestones.

### 2.2 Deterministic Core

Core application behavior shall be deterministic wherever practical.

Use deterministic application logic for:

- Scope validation.
- Scanner input validation.
- Scanner execution.
- Result parsing.
- Database persistence.
- State transitions.
- Approval enforcement.
- Report generation.

Use the LLM for tasks requiring language understanding or synthesis, such as:

- Interpreting assessment requests.
- Explaining assessment plans.
- Summarizing findings.
- Correlating potentially related findings.
- Explaining risk.
- Producing remediation recommendations.

The LLM shall not replace deterministic safety enforcement.

### 2.3 Test Before Expansion

Do not proceed to a dependent milestone while its required acceptance criteria remain unmet.

When a milestone fails:

1. Inspect the failure.
2. Identify the underlying cause.
3. Fix the relevant component.
4. Rerun the affected tests.
5. Verify that previous functionality still works.

### 2.4 No Unnecessary Complexity

The MVP shall avoid introducing:

- Microservices.
- Distributed task queues.
- Kubernetes.
- Complex authentication systems.
- Unnecessary frontend frameworks.
- Unnecessary database abstractions.
- Unrequested scanner integrations.

Additional complexity requires a clear MVP justification.

---

## 3. Existing Environment

The following setup has already been completed and verified by the developer:

- Python environment.
- Nmap installation.
- OWASP ZAP installation.
- Required Python libraries.
- OpenAI API key.
- `.env` configuration.

The implementation shall reuse the existing environment.

Do not recreate the environment or reinstall tools unnecessarily.

Before development, verify that the existing scanner installations and API configuration remain functional.

The application shall not expose API keys in source code, logs, reports, or UI output.

---

## 4. Proposed Project Structure

The initial project structure shall follow this organization:

```text
project/
│
├── app.py
├── requirements.txt
├── .env
├── .gitignore
│
├── docs/
│   ├── 01_PRD.md
│   ├── 02_TRD.md
│   ├── 03_APP_FLOW.md
│   ├── 04_UI_UX_DESIGN_BRIEF.md
│   ├── 05_BACKEND_SCHEMA.md
│   ├── 06_IMPLEMENTATION_PLAN.md
│   ├── 07_AGENT_BEHAVIOR.md
│   ├── 08_TOOL_CONTRACTS.md
│   └── 09_SAFETY_RULES.md
│
├── src/
│   ├── database/
│   ├── models/
│   ├── scope/
│   ├── agent/
│   ├── scanners/
│   ├── parsers/
│   ├── findings/
│   ├── approvals/
│   ├── reporting/
│   └── ui/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── data/
│   ├── database/
│   └── scanner_outputs/
│
└── reports/
```

This structure is a proposed organization.

The implementation may adjust directory names when necessary, but responsibilities shall remain separated.

The `.env` file, database files, raw scanner outputs, generated reports, and other sensitive runtime artifacts shall not be committed to Git unless explicitly intended and safe.

---

## 5. Milestone 0 — Project Foundation

### Objective

Establish a clean application structure and verify that the existing development environment works.

### Tasks

1. Inspect the existing project.
2. Preserve working configuration.
3. Create the required source directories.
4. Create the test directories.
5. Configure `.gitignore`.
6. Verify environment-variable loading.
7. Verify OpenAI API connectivity.
8. Verify Nmap availability.
9. Verify OWASP ZAP availability.
10. Verify Nikto availability if already installed.
11. Confirm the application can launch.

### Deliverables

- Organized project structure.
- Working Python environment.
- Environment configuration.
- Initial application entry point.
- Basic test setup.

### Acceptance Criteria

- The application launches.
- Required environment variables are loaded.
- Missing API configuration produces a clear error.
- Scanner availability can be checked.
- API keys are not printed.
- Existing installations are reused.

---

## 6. Milestone 1 — Database and Persistence Layer

### Objective

Implement the SQLite database and persistence operations.

### Tasks

1. Create the SQLite database.
2. Implement schema creation.
3. Enable foreign-key enforcement.
4. Implement assessment creation.
5. Implement assessment retrieval.
6. Implement assessment updates.
7. Implement scope persistence.
8. Implement plan persistence.
9. Implement scanner execution persistence.
10. Implement finding persistence.
11. Implement evidence persistence.
12. Implement approval persistence.
13. Implement report persistence.
14. Implement audit-event persistence.

### Deliverables

- Database initialization.
- Persistence functions.
- Schema validation.
- Database tests.

### Acceptance Criteria

- Assessments can be created and retrieved.
- Foreign keys are enforced.
- Related records reference valid assessments.
- Invalid state values are rejected.
- Database operations preserve data integrity.
- Tests verify the required schema relationships.

---

## 7. Milestone 2 — Scope Validation

### Objective

Implement deterministic assessment scope validation.

### Tasks

1. Parse target input.
2. Validate supported target formats.
3. Normalize target representation.
4. Parse authorized scope.
5. Parse exclusions.
6. Check target against authorized scope.
7. Record validation results.
8. Block invalid or unauthorized targets.
9. Prevent scanner execution before successful validation.

### Deliverables

- Scope validation module.
- Scope persistence.
- Scope validation tests.

### Acceptance Criteria

- Valid authorized lab targets can proceed.
- Invalid targets are rejected.
- Excluded targets are rejected.
- Ambiguous scope is not silently accepted.
- Scope validation results are persisted.
- Scanner execution cannot bypass scope validation.

---

## 8. Milestone 3 — Scanner Adapter Foundation

### Objective

Create a consistent interface for scanner integrations.

### Tasks

1. Define scanner adapter responsibilities.
2. Define validated scanner input structures.
3. Define scanner execution results.
4. Define execution status handling.
5. Implement scanner availability checks.
6. Implement timeout handling.
7. Implement error handling.
8. Implement output preservation.
9. Implement execution metadata recording.

### Deliverables

- Scanner adapter interface.
- Execution result structure.
- Scanner availability checks.
- Adapter tests.

### Acceptance Criteria

- Scanner operations use a consistent interface.
- Inputs are validated before execution.
- Execution outcomes are recorded.
- Scanner errors are represented accurately.
- Original output can be preserved.
- Scanner execution does not bypass scope validation.

---

## 9. Milestone 4 — Nmap Integration

### Objective

Implement the first working scanner integration.

### Tasks

1. Verify Nmap availability.
2. Implement the approved Nmap operation.
3. Validate target and scan parameters.
4. Execute Nmap through the scanner adapter.
5. Apply execution time limits.
6. Capture output.
7. Record execution metadata.
8. Parse supported output.
9. Persist discovered assets and findings where applicable.

### Deliverables

- Working Nmap adapter.
- Nmap parser.
- Execution persistence.
- Integration tests.

### Acceptance Criteria

- Nmap can execute against an authorized lab target.
- The operation uses validated inputs.
- Scanner output is preserved.
- Execution status is recorded.
- Supported output is parsed.
- Discovered assets are associated with the assessment.
- Unauthorized targets are rejected.

---

## 10. Milestone 5 — OWASP ZAP Integration

### Objective

Implement the initial web application scanner integration.

### Tasks

1. Verify ZAP availability.
2. Define supported integration mode.
3. Configure the approved scan operation.
4. Validate target and scope.
5. Execute the scan.
6. Apply timeout handling.
7. Capture scanner output.
8. Parse supported findings.
9. Persist execution metadata.
10. Persist findings and evidence references.

### Deliverables

- Working ZAP adapter.
- ZAP result parser.
- Execution persistence.
- Integration tests.

### Acceptance Criteria

- ZAP can execute against an authorized lab web target.
- Scanner inputs are validated.
- Execution status is accurate.
- Findings are parsed into structured data.
- Original output is preserved.
- Scope restrictions are enforced.
- Failed executions are reported accurately.

---

## 11. Milestone 6 — Nikto Integration

### Objective

Implement the initial Nikto integration.

### Tasks

1. Verify Nikto availability.
2. Define supported execution mode.
3. Validate target and scope.
4. Execute the approved operation.
5. Apply timeout handling.
6. Capture output.
7. Parse supported results.
8. Persist execution metadata.
9. Persist findings and evidence references.

### Deliverables

- Working Nikto adapter.
- Nikto result parser.
- Execution persistence.
- Integration tests.

### Acceptance Criteria

- Nikto can execute against an authorized lab target.
- Scanner inputs are validated.
- Execution outcomes are recorded.
- Supported results are parsed.
- Original output is preserved.
- Failures are reported accurately.

### Integration Status

The application shall distinguish a verified Nikto integration from an installed but unverified integration.

---

## 12. Milestone 7 — Finding Normalization and Evidence

### Objective

Create a common finding representation across scanner integrations.

### Tasks

1. Define normalized finding fields.
2. Implement scanner-specific parsers.
3. Normalize severity.
4. Normalize affected assets.
5. Preserve scanner-native identifiers.
6. Create finding-source records.
7. Create evidence records.
8. Associate findings with assessments.
9. Validate finding data.
10. Handle missing fields.

### Deliverables

- Finding normalization module.
- Evidence persistence.
- Finding-source persistence.
- Parser fixtures.
- Unit tests.

### Acceptance Criteria

- Supported scanner findings use the common schema.
- Original scanner identifiers are preserved.
- Findings reference their source execution.
- Evidence is traceable.
- Missing values are not fabricated.
- Scanner-native severity is preserved.
- Parsing failures do not silently discard original output.

---

## 13. Milestone 8 — Finding Correlation and Deduplication

### Objective

Identify duplicate or related findings without losing source evidence.

### Tasks

1. Define correlation criteria.
2. Compare affected assets.
3. Compare finding categories.
4. Compare scanner-native identifiers.
5. Compare endpoint or service information.
6. Identify potential duplicates.
7. Preserve distinct findings.
8. Record correlation rationale.
9. Support analyst review of uncertain correlations.

### Deliverables

- Correlation module.
- Correlation persistence.
- Unit tests.

### Acceptance Criteria

- Exact duplicate findings can be identified.
- Distinct affected assets are preserved.
- Correlation decisions are recorded.
- Original scanner evidence remains available.
- Uncertain findings are not automatically merged.

---

## 14. Milestone 9 — Assessment Workflow and Agent Planning

### Objective

Implement the application workflow and LLM-assisted assessment planning.

### Tasks

1. Implement assessment creation.
2. Integrate scope validation.
3. Define structured assessment-plan output.
4. Validate plan structure.
5. Generate plan explanations.
6. Display the plan.
7. Record analyst acceptance or rejection.
8. Execute only accepted plans.
9. Track workflow state.
10. Handle invalid or incomplete agent output.

### Deliverables

- Assessment workflow.
- Agent planning module.
- Plan persistence.
- Workflow tests.

### Acceptance Criteria

- Assessment requests can be submitted.
- Scope validation occurs before planning execution.
- The agent produces a structured plan.
- Invalid plan output is rejected.
- Analyst review is required.
- Only accepted plans authorize scanner execution.
- Workflow state is persisted.

---

## 15. Milestone 10 — Risk Analysis and Finding Review

### Objective

Provide evidence-grounded analysis and prioritization.

### Tasks

1. Define the risk-prioritization method.
2. Use available severity and CVSS information.
3. Incorporate relevant exposure information.
4. Incorporate asset impact where supported.
5. Incorporate confidence.
6. Generate finding explanations.
7. Generate remediation recommendations.
8. Preserve source evidence.
9. Display findings for analyst review.

### Deliverables

- Risk prioritization module.
- Finding analysis module.
- Review interface.
- Unit tests.

### Acceptance Criteria

- Findings can be prioritized using documented criteria.
- Risk explanations reference available evidence.
- Missing information is identified.
- The system does not invent CVSS or CVE data.
- Analyst review is supported.
- Remediation recommendations are traceable to the finding.

---

## 16. Milestone 11 — Approval Workflow

### Objective

Implement explicit human approval for active validation.

### Tasks

1. Define active-validation proposal structure.
2. Create approval records.
3. Display the proposed action.
4. Display target and scope.
5. Display potential impact.
6. Implement approve, reject, and defer.
7. Record analyst decisions.
8. Verify approval before execution.
9. Record execution outcome.
10. Handle scope changes.

### Deliverables

- Approval module.
- Approval interface.
- Approval persistence.
- Safety tests.

### Acceptance Criteria

- Active validation requires explicit approval.
- The LLM cannot approve its own proposal.
- Rejected actions do not execute.
- Deferred actions do not execute.
- Approval decisions are persisted.
- Execution references the approval.
- Scope changes invalidate relevant approvals.
- Execution outcome is recorded separately from approval.

---

## 17. Milestone 12 — PDF Report Generation

### Objective

Generate a traceable assessment report from persisted data.

### Tasks

1. Define report structure.
2. Retrieve assessment data.
3. Retrieve scope information.
4. Retrieve scanner execution outcomes.
5. Retrieve normalized findings.
6. Retrieve evidence references.
7. Retrieve approval history.
8. Include limitations.
9. Generate PDF.
10. Persist report metadata.
11. Support report download.
12. Handle generation errors.

### Deliverables

- PDF report generator.
- Report persistence.
- Report tests.
- Example report from a completed lab assessment.

### Acceptance Criteria

- Reports are generated from persisted data.
- Findings reference source evidence.
- Scope is included.
- Scanner failures are disclosed.
- Limitations are disclosed.
- Approval history is included where relevant.
- Report generation status is persisted.
- Successful reports can be downloaded.
- Failed report generation does not corrupt assessment data.

---

## 18. Milestone 13 — Streamlit Dashboard

### Objective

Implement the user interface after the underlying assessment workflow is functional.

### Tasks

1. Implement navigation.
2. Implement dashboard.
3. Implement assessment creation.
4. Implement scope validation display.
5. Implement plan review.
6. Implement scanner progress.
7. Implement findings table.
8. Implement finding details.
9. Implement approval interface.
10. Implement report generation.
11. Implement report download.
12. Implement integration status.

### Deliverables

- Streamlit dashboard.
- Assessment pages.
- Findings review interface.
- Approval interface.
- Report interface.

### Acceptance Criteria

- The complete assessment workflow can be operated through the UI.
- Status values reflect persisted application state.
- Scanner failures are visible.
- Evidence is accessible.
- Approval actions are explicit.
- Report downloads work.
- UI actions do not bypass backend validation.

---

## 19. Milestone 14 — End-to-End Testing

### Objective

Verify the complete assessment workflow.

### Tasks

1. Create an authorized lab assessment.
2. Validate scope.
3. Generate an assessment plan.
4. Review and accept the plan.
5. Execute supported scanners.
6. Process scanner results.
7. Normalize findings.
8. Correlate findings.
9. Review risk analysis.
10. Test approval behavior.
11. Generate the PDF.
12. Verify report content.
13. Verify assessment state.
14. Verify audit events.

### Deliverables

- End-to-end test suite.
- Test assessment.
- Verified PDF report.
- Test results.

### Acceptance Criteria

- The complete workflow operates against an authorized lab target.
- Scanner execution outcomes are recorded.
- Findings are traceable.
- Approval enforcement works.
- Reports reflect actual results.
- Failure paths are tested.
- No fabricated scanner output is used in the final demonstration.

---

## 20. Milestone 15 — Demo Preparation

### Objective

Prepare a reliable and honest hackathon demonstration.

### Tasks

1. Select an authorized lab target.
2. Verify scanner availability.
3. Run a complete assessment.
4. Verify result parsing.
5. Verify findings.
6. Verify approval behavior.
7. Generate the report.
8. Prepare a demonstration sequence.
9. Prepare fallback screenshots or saved results.
10. Document known limitations.

### Deliverables

- Demonstration assessment.
- Demonstration report.
- Demo sequence.
- Known limitations.

### Acceptance Criteria

- The demonstration uses an authorized target.
- The application operates reliably.
- Results are traceable.
- The report is generated successfully.
- Scanner limitations are disclosed.
- Demonstration fallback data is clearly labeled.
- No unsupported functionality is presented as implemented.

---

## 21. Milestone Dependencies

The implementation order shall follow these dependencies:

| Milestone | Depends on |
|---|---|
| Project Foundation | Existing environment |
| Database | Project Foundation |
| Scope Validation | Database |
| Scanner Adapter Foundation | Project Foundation, Scope Validation |
| Nmap Integration | Scanner Adapter Foundation |
| ZAP Integration | Scanner Adapter Foundation |
| Nikto Integration | Scanner Adapter Foundation |
| Finding Normalization | Scanner integrations |
| Correlation | Finding Normalization |
| Assessment Workflow | Database, Scope Validation, Scanner Adapter Foundation |
| Risk Analysis | Finding Normalization |
| Approval Workflow | Assessment Workflow, Findings |
| PDF Reporting | Database, Findings, Evidence, Approval |
| Dashboard | Functional backend workflow |
| End-to-End Testing | Core milestones |
| Demo Preparation | End-to-End Testing |

Milestones may be developed in parallel only when their dependencies are satisfied and integration boundaries are clear.

---

## 22. Testing Strategy

### Unit Tests

Test individual components:

- Scope validation.
- Input validation.
- Parsers.
- Normalization.
- Correlation.
- Risk calculations.
- State transitions.
- Approval enforcement.
- Report data preparation.

### Integration Tests

Test:

- Scanner adapters.
- Database persistence.
- Scanner result ingestion.
- Approval execution checks.
- Report generation.

### End-to-End Tests

Test the full workflow against an authorized lab target.

### Failure Tests

Test:

- Invalid target.
- Unauthorized target.
- Scanner unavailable.
- Scanner timeout.
- Malformed output.
- Missing evidence.
- Invalid agent response.
- Rejected approval.
- Report generation failure.

### Test Data

Use:

- Controlled lab targets.
- Saved scanner outputs.
- Parser fixtures.
- Synthetic records clearly marked as test data.

Synthetic data shall not be presented as real assessment results.

---

## 23. Development Rules for Antigravity

Antigravity shall follow these rules during implementation:

1. Read the relevant project documents before coding.
2. Inspect the existing repository before modifying files.
3. Preserve existing working functionality.
4. Implement only the currently approved milestone.
5. Avoid implementing future milestones prematurely.
6. Use the defined database schema.
7. Use the defined scanner adapter interface.
8. Keep scanner-specific parsing separate.
9. Keep LLM reasoning separate from deterministic safety enforcement.
10. Validate structured LLM output.
11. Write tests for implemented functionality.
12. Run the relevant tests after changes.
13. Report test results accurately.
14. Report incomplete work explicitly.
15. Do not fabricate successful execution.
16. Do not silently modify project requirements.
17. Ask for clarification when a requirement is ambiguous or contradictory.
18. Do not introduce unnecessary dependencies.
19. Do not expose API keys.
20. Do not proceed to the next milestone without review.

---

## 24. Milestone Completion Report

After completing a milestone, Antigravity shall provide:

### Summary

What was implemented.

### Files Changed

List of created and modified files.

### Tests

- Tests executed.
- Test results.
- Failed tests.
- Tests not executed.

### Verification

What was manually or automatically verified.

### Limitations

What remains incomplete.

### Next Milestone

The next milestone and its dependencies.

Antigravity shall not claim completion if required acceptance criteria remain unmet.

---

## 25. MVP Completion Criteria

The MVP is complete when:

- The application can create assessments.
- Scope validation is enforced.
- The agent can generate structured assessment plans.
- The analyst can review plans.
- At least three scanner integrations or supported scanner-result ingestion workflows are operational, as required by the approved project scope.
- Scanner execution outcomes are tracked.
- Findings are normalized.
- Evidence is preserved.
- Duplicate findings are handled.
- Findings can be prioritized.
- Active validation requires explicit approval.
- Approval decisions are recorded.
- A PDF report can be generated.
- The dashboard supports the complete workflow.
- End-to-end testing has been completed.
- Known limitations are documented.

The exact scanner capabilities demonstrated shall be stated accurately.

---

## 26. Final Implementation Principle

The project shall prioritize a reliable, evidence-backed assessment workflow over the number of features.

A smaller implementation that correctly validates scope, executes supported scanners, preserves evidence, records approvals, and generates an accurate report is preferable to a larger implementation with unreliable or unverified functionality.

---

## 27. Relationship to Other Documents

This document defines the implementation sequence.

The remaining documents shall define:

- 07_AGENT_BEHAVIOR.md — agent reasoning and planning.
- 08_TOOL_CONTRACTS.md — scanner adapter contracts.
- 09_SAFETY_RULES.md — safety enforcement.

Implementation shall remain consistent with the PRD, TRD, application flow, UI/UX brief, and backend schema.
