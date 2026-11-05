# AI-Powered Unified VAPT Agent
## Technical Requirements Document (TRD)

**Version:** 1.0 — Initial technical design  
**Status:** Proposed  
**Related document:** 01_PRD.md

---

## 1. Purpose

This document defines the proposed technical architecture, implementation technologies, system components, data flow, integration strategy, and technical constraints for the AI-powered Unified VAPT Agent.

The implementation must satisfy the mandatory requirements in the hackathon problem statement and the approved PRD.

This document does not claim that proposed integrations or features are already implemented.

---

## 2. Technical Objectives

The architecture shall:

1. Support authorized security assessments against explicitly scoped targets.
2. Execute and orchestrate approved scanner integrations.
3. Preserve scanner output and evidence.
4. Normalize findings into a common data model.
5. Use an LLM for evidence-grounded analysis and decision support.
6. Support risk prioritization and finding correlation.
7. Enforce human approval before active exploitation or offensive validation.
8. Generate a downloadable PDF assessment report.
9. Record assessment actions and outcomes.
10. Remain practical for a solo developer building a hackathon prototype.

---

## 3. Proposed Technology Stack

### 3.1 Application

| Component | Technology | Purpose |
|---|---|---|
| Programming language | Python | Core application and orchestration |
| User interface | Streamlit | Assessment dashboard and analyst interaction |
| Database | SQLite | Assessment and finding persistence |
| Data validation | Pydantic | Structured data validation |
| AI integration | OpenAI Python SDK | Evidence-grounded reasoning and analysis |
| HTTP communication | Requests | Scanner API communication |
| PDF generation | ReportLab | Assessment report generation |
| Testing | pytest | Unit and integration testing |
| Code quality | Ruff and Bandit | Linting and security checks |
| Container runtime | Docker Desktop | Isolated scanner and demo-target execution |
| Version control | Git and GitHub | Source control |

The stack is proposed for the MVP. Changes require an explicit project decision.

### 3.2 Scanner Integrations

The initial planned scanner integrations are:

| Scanner | Category | Proposed execution |
|---|---|---|
| Nmap | Network | Local executable |
| OWASP ZAP | Web | Local application or API |
| Nikto | Web | Docker container |

The application shall use a scanner adapter interface so scanner-specific implementation details do not leak into the finding-processing logic.

### 3.3 Integration Status

At the time of this document:

- Nmap executable: verified working.
- Nikto Docker image: downloaded and version execution verified.
- Nikto target scan: not yet verified.
- OWASP ZAP installation: verified by the user.
- OWASP ZAP API integration: not yet verified.
- Finding normalization: not yet implemented.
- PDF generation: not yet implemented.

The final demonstration must distinguish verified capabilities from planned capabilities.

---

## 4. System Architecture

The proposed application consists of the following logical components:

1. User Interface.
2. Assessment Manager.
3. Scope Validator.
4. Agent Planner.
5. Scanner Orchestrator.
6. Scanner Adapters.
7. Result Parsers.
8. Finding Normalizer.
9. Finding Correlation and Risk Analysis.
10. Human Approval Manager.
11. Report Generator.
12. Persistence Layer.

### 4.1 Component Responsibilities

#### User Interface

The interface shall:

- Accept assessment requests.
- Display target and scope information.
- Show the proposed assessment plan.
- Display assessment progress.
- Present findings and evidence.
- Present approval requests.
- Provide report download functionality.

#### Assessment Manager

The assessment manager shall:

- Create assessment records.
- Coordinate assessment state.
- Track execution status.
- Connect assessment requests to plans, scanner results, findings, approvals, and reports.

#### Scope Validator

The scope validator shall:

- Validate target input.
- Check the requested target against the approved scope.
- Reject unauthorized targets.
- Prevent scanner execution when scope validation fails.
- Preserve scope information for auditability.

The scope validator must not rely solely on the LLM.

#### Agent Planner

The planner shall:

- Interpret the assessment request.
- Consider approved scope and discovered assets.
- Select relevant scanners.
- Explain the purpose of selected tools.
- Identify prerequisites and dependencies.
- Avoid unnecessary repeated scans.

The planner shall produce structured plans rather than arbitrary shell commands.

#### Scanner Orchestrator

The orchestrator shall:

- Execute approved scanner jobs.
- Track job state.
- Collect outputs.
- Handle errors and timeouts.
- Record execution metadata.
- Enforce scanner-specific execution restrictions.

#### Scanner Adapters

Each scanner adapter shall provide a consistent interface for:

- Capability description.
- Input validation.
- Execution.
- Status retrieval.
- Output collection.
- Error reporting.

Scanner adapters shall not independently authorize targets.

#### Result Parsers

The parser layer shall convert scanner-specific outputs into structured intermediate data.

The original scanner output shall remain available for traceability.

#### Finding Normalizer

The normalizer shall convert structured scanner results into the common finding schema.

It shall preserve:

- Original tool identifiers.
- Original severity.
- Asset information.
- Evidence.
- Source references.
- Confidence and validation status.

#### Finding Correlation

The correlation component shall:

- Identify potential duplicate findings.
- Merge genuine duplicates.
- Preserve distinct affected assets.
- Preserve evidence from each contributing scanner.
- Avoid merging findings solely because their titles match.

#### Risk Analysis

The risk-analysis component shall evaluate findings using available severity, exposure, exploitability, asset impact, and confidence information.

Missing information shall be represented as unknown rather than fabricated.

#### Human Approval Manager

The approval manager shall:

- Present proposed active validation actions.
- Require explicit analyst approval.
- Record the proposed action.
- Record the approving user.
- Record the decision and timestamp.
- Record the execution outcome.

The system shall not treat an LLM-generated recommendation as approval.

#### Report Generator

The report generator shall:

- Retrieve assessment data.
- Produce executive and technical report sections.
- Include evidence-backed findings.
- Include remediation recommendations.
- Include scope and methodology.
- Include limitations and scan failures.
- Generate a downloadable PDF.

#### Persistence Layer

The persistence layer shall store assessment records, scope, execution records, assets, findings, evidence references, approvals, and report metadata.

SQLite is the proposed MVP database.

---

## 5. Assessment Data Flow

The proposed data flow is:

1. Analyst submits an assessment request.
2. Application records the request and scope.
3. Scope validator checks the requested target.
4. Agent planner creates a structured assessment plan.
5. Analyst reviews the plan.
6. Scanner orchestrator executes permitted scans.
7. Scanner adapters collect outputs.
8. Parsers convert scanner outputs into structured data.
9. Normalizer creates common finding records.
10. Correlation component identifies potential duplicates.
11. Risk analysis prioritizes findings.
12. Analyst reviews findings.
13. Active validation requires explicit approval.
14. Approved validation is executed and recorded.
15. Report generator creates the PDF.
16. Assessment records remain available for review.

The application shall not skip scope validation.

---

## 6. Scanner Adapter Requirements

### 6.1 Common Adapter Contract

Each adapter shall expose:

- Scanner identifier.
- Scanner version, when available.
- Supported assessment category.
- Supported execution mode.
- Input validation.
- Execution method.
- Job status.
- Result collection.
- Error reporting.

### 6.2 Nmap Adapter

The Nmap adapter shall:

- Invoke the installed Nmap executable.
- Accept only validated targets within approved scope.
- Use explicitly configured scan profiles.
- Capture process output.
- Capture execution status.
- Capture scanner version.
- Preserve the original scan output.
- Parse supported network findings.

The adapter shall not accept arbitrary commands from the LLM.

### 6.3 OWASP ZAP Adapter

The ZAP adapter shall:

- Communicate with the configured ZAP instance.
- Validate the target against assessment scope.
- Execute approved scan operations.
- Collect alerts and supporting evidence.
- Record execution status.
- Preserve references to the original ZAP results.

The implementation shall use a supported ZAP interface.

The exact API workflow and configuration remain to be verified.

### 6.4 Nikto Adapter

The Nikto adapter shall:

- Invoke the configured Nikto Docker image.
- Validate the target before execution.
- Use a controlled container invocation.
- Capture output and exit status.
- Record image and scanner version.
- Parse supported web-server findings.
- Preserve original output.

The application shall not expose unrestricted Docker command execution to the LLM.

### 6.5 Scanner Failure Handling

Scanner failures shall be represented as execution failures, not as successful assessments.

The application shall distinguish:

- Not started.
- Running.
- Completed.
- Failed.
- Timed out.
- Cancelled.

An assessment with scanner failures shall disclose those failures in its report.

---

## 7. Common Finding Data Model

The application shall use a common finding representation.

Each finding shall support:

- Unique finding identifier.
- Assessment identifier.
- Title.
- Description.
- Affected asset.
- Finding category.
- Severity.
- CVSS information, when available.
- CVE reference, when applicable.
- CWE reference, when applicable.
- Confidence.
- Validation status.
- Evidence references.
- Source scanner references.
- Remediation recommendation.
- Creation and update timestamps.

The exact schema will be defined in 05_BACKEND_SCHEMA.md.

The implementation shall preserve scanner-native fields where useful.

Missing values shall remain missing or explicitly unknown.

---

## 8. AI Reasoning Requirements

The LLM shall support:

- Natural-language request interpretation.
- Structured assessment planning.
- Explanation of scanner selection.
- Evidence-grounded finding analysis.
- Finding summarization.
- Correlation suggestions.
- Risk-analysis explanations.
- Remediation recommendations.
- Report narrative generation.

The LLM shall not:

- Invent scanner results.
- Invent CVEs.
- Invent evidence.
- Fabricate scan completion.
- Bypass scope validation.
- Directly execute arbitrary shell commands.
- Approve its own active validation actions.
- Override application-enforced safety rules.

LLM outputs shall be validated against structured schemas before being used by the application.

The application shall preserve the distinction between observed evidence and model-generated interpretation.

---

## 9. Security Requirements

### 9.1 Scope Enforcement

Scope validation shall be performed by deterministic application logic.

Scanner execution shall require a validated assessment scope.

### 9.2 Tool Execution

Scanner execution shall use predefined adapter operations.

The LLM shall not construct unrestricted shell commands.

### 9.3 Approval

Active exploitation and offensive validation shall require explicit human approval.

The approval manager shall record the decision and outcome.

### 9.4 Secrets

API keys and scanner credentials shall not be hardcoded.

Secrets shall not be included in source control or assessment reports.

### 9.5 Evidence

Scanner output and evidence shall be treated as untrusted data.

Evidence shall not be interpreted as executable instructions.

### 9.6 Auditability

The system shall record assessment actions, scanner execution outcomes, approval decisions, and report generation events.

### 9.7 Data Handling

The application shall avoid unnecessary collection of sensitive data and shall restrict access to assessment evidence according to the prototype's supported security model.

---

## 10. Persistence Requirements

SQLite shall persist:

- Assessments.
- Assessment scope.
- Assets.
- Scanner executions.
- Findings.
- Evidence references.
- Approval records.
- Report metadata.

The database shall support retrieving all findings and execution records associated with an assessment.

The database schema shall be documented separately.

---

## 11. Report Generation

ReportLab shall be used to generate the PDF report.

The report generator shall retrieve structured assessment data rather than relying on an LLM to create the entire report without validation.

The PDF shall contain:

- Executive summary.
- Assessment scope.
- Methodology.
- Tool execution summary.
- Severity distribution.
- Detailed findings.
- Evidence.
- Remediation.
- Limitations.
- Scan failures.
- Approval records.
- Assessment timestamps.

The report shall not claim that unexecuted scans were completed.

---

## 12. Testing Strategy

### Unit Tests

Test:

- Scope validation.
- Scanner input validation.
- Output parsing.
- Finding normalization.
- Duplicate detection.
- Risk calculations.
- Approval-state transitions.
- Report data generation.

### Integration Tests

Test:

- Nmap adapter execution.
- Nikto container execution.
- ZAP communication.
- Scanner output ingestion.
- Database persistence.
- PDF generation.

### Safety Tests

Test:

- Out-of-scope target rejection.
- Invalid target rejection.
- Scanner failure handling.
- Timeout handling.
- Missing evidence handling.
- Approval requirement enforcement.
- Rejection of arbitrary LLM-generated commands.

### Demonstration Tests

The prototype shall be tested against an explicitly authorized lab target.

The demonstration shall show:

- Request submission.
- Scope validation.
- Assessment plan.
- Scanner execution.
- Finding normalization.
- Evidence traceability.
- Risk prioritization.
- Approval gate.
- Report generation.

---

## 13. Proposed Implementation Constraints

The initial implementation shall:

- Favor a single Python application.
- Use Streamlit for the MVP interface.
- Use SQLite for persistence.
- Use explicit scanner adapters.
- Avoid unnecessary distributed services.
- Avoid unrestricted agent tool execution.
- Avoid requiring all seven named scanners to be live integrations.
- Keep the system testable without requiring every scanner to be available.

FastAPI, PostgreSQL, Redis, Celery, and complex multi-agent frameworks are not part of the initial architecture unless a later documented requirement justifies them.

---

## 14. Technical Risks and Open Decisions

### 14.1 Scanner Integration

The exact execution and parsing workflows for Nmap, ZAP, and Nikto must be verified.

### 14.2 Docker Target Connectivity

The application must verify that containerized Nikto can reach the intended authorized target.

### 14.3 ZAP Configuration

The required ZAP API configuration, scan mode, and result format must be determined during implementation.

### 14.4 Finding Correlation

Duplicate detection must avoid merging distinct vulnerabilities or assets.

### 14.5 AI Reliability

LLM outputs must be validated and grounded in scanner evidence.

### 14.6 Approval Enforcement

Approval must be enforced by application logic rather than prompt instructions alone.

### 14.7 Report Completeness

The PDF must disclose missing data, scanner failures, and limitations.

---

## 15. Acceptance Criteria

The technical implementation shall be considered ready for the hackathon demonstration when:

1. The application starts successfully.
2. The analyst can submit an assessment request.
3. Scope validation is enforced.
4. The agent produces a structured assessment plan.
5. At least three working integrations or supported imports are demonstrated.
6. Network and web coverage are demonstrated.
7. Scanner outputs are preserved.
8. Findings are normalized.
9. Duplicate handling preserves distinct assets and evidence.
10. Risk prioritization is supported.
11. Active validation requires explicit approval.
12. Approval decisions are recorded.
13. A professional PDF report is generated.
14. Report findings are traceable to source evidence.
15. Failures and limitations are disclosed.

---

## 16. Relationship to Other Documents

This document defines the proposed technical architecture.

The following documents shall provide the implementation detail:

- 03_APP_FLOW.md — user and system workflows.
- 04_UI_UX_DESIGN_BRIEF.md — interface requirements.
- 05_BACKEND_SCHEMA.md — persistent data structures.
- 06_IMPLEMENTATION_PLAN.md — development milestones.
- 07_AGENT_BEHAVIOR.md — agent reasoning and planning behavior.
- 08_TOOL_CONTRACTS.md — scanner adapter interfaces.
- 09_SAFETY_RULES.md — application-enforced safety boundaries.

Any conflict with the PRD or hackathon problem statement must be resolved before implementation.
