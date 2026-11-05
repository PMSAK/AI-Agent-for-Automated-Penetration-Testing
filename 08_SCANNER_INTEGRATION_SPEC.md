# 08 — Scanner Integration Specification

**Project:** Unified VAPT Agent  
**Document:** Scanner Integration Specification  
**Version:** 1.0  
**Status:** Implementation Reference

---

## 1. Purpose

This document defines the scanner integration architecture for the Unified VAPT Agent.

The application integrates three security assessment tools:

1. Nmap
2. OWASP ZAP
3. Nikto

Each scanner must be integrated through a dedicated Python adapter.

The purpose of this architecture is to allow the application to execute scanner operations, capture their outputs, handle failures, and convert results into a common finding format.

The LLM must not directly execute scanner commands.

---

## 2. Integration Architecture

The scanner integration workflow is:

User Request  
→ Scope Validation  
→ Agent Assessment Plan  
→ Operation Validation  
→ Scanner Adapter  
→ Scanner Execution  
→ Output Capture  
→ Output Parser  
→ Finding Normalization  
→ Database Persistence

Each scanner adapter is responsible for communicating with its scanner.

The agent is responsible for recommending operations.

The application is responsible for validating and executing those operations.

### Architecture Rules

- Every scanner must have a dedicated adapter.
- Scanner operations must be predefined and allowlisted.
- Scanner inputs must be validated before execution.
- Scanner outputs must be captured.
- Scanner errors must be recorded.
- Findings must be normalized before persistence.
- Scanner execution must not depend on arbitrary LLM-generated shell commands.

---

## 3. Scanner Adapter Interface

All scanner adapters must follow a common interface.

Each adapter should support:

### 3.1 Availability Check

Determine whether the scanner is installed and accessible.

Return:
- Scanner name.
- Availability status.
- Version, when obtainable.
- Error information, if unavailable.

### 3.2 Supported Operations

Expose the scanner operations supported by the application.

The agent may select only operations returned by the adapter's capability definitions.

### 3.3 Input Validation

Validate:
- Target.
- Target type.
- Operation identifier.
- Operation-specific parameters.
- Scope restrictions.

Invalid inputs must be rejected before execution.

### 3.4 Execution

Execute the selected operation using the scanner's supported interface.

The adapter must:
- Use validated inputs.
- Apply configured restrictions.
- Capture output.
- Capture errors.
- Track execution duration.
- Handle timeout and cancellation.

### 3.5 Output Parsing

Convert scanner output into structured data.

The parser must preserve:
- Original scanner finding.
- Scanner source.
- Relevant evidence.
- Target information.
- Available severity.
- Available vulnerability identifiers.

### 3.6 Execution Result

Every scanner operation must return a structured execution result.

Suggested fields:

```json
{
  "scanner": "scanner_name",
  "operation": "operation_id",
  "target": "validated_target",
  "status": "completed",
  "started_at": "timestamp",
  "completed_at": "timestamp",
  "duration_seconds": 0,
  "findings": [],
  "stdout": "",
  "stderr": "",
  "error": null
}
```

This is a conceptual schema. The implementation should use the project's actual data models.

---

## 4. Scanner Capability Registry

The application must maintain a registry of available scanner operations.

The registry must define:

- Scanner identifier.
- Operation identifier.
- Description.
- Supported target types.
- Input requirements.
- Risk classification.
- Approval requirement.
- Output format.
- Parser.

The LLM must select from this registry.

It must not invent operation identifiers.

### Example

```python
SCANNER_CAPABILITIES = {
    "nmap": {
        "available": False,
        "operations": []
    },
    "zap": {
        "available": False,
        "operations": []
    },
    "nikto": {
        "available": False,
        "operations": []
    }
}
```

The values above are placeholders.

Actual availability must be detected at runtime.

---

## 5. Nmap Integration

### 5.1 Purpose

Nmap is used for authorized host and service discovery.

The application should use Nmap to identify relevant information about the explicitly authorized target.

### 5.2 Adapter Responsibilities

The Nmap adapter must:

- Check whether Nmap is installed.
- Detect its version when possible.
- Validate the target.
- Expose supported scan operations.
- Execute approved operations.
- Capture output.
- Parse service and host information.
- Record failures.

### 5.3 Target Restrictions

The adapter must receive a validated target.

It must not:
- Accept arbitrary target expansion from the LLM.
- Automatically scan neighboring addresses.
- Scan discovered hosts without scope validation.
- Accept unrestricted command-line arguments.

### 5.4 Output Handling

The adapter should prefer a structured output format supported by Nmap.

The parser should extract, when available:

- Host status.
- IP address.
- Hostname.
- Port.
- Protocol.
- Service name.
- Service version.
- Scanner warnings.

The parser must not infer a service version when the scanner did not provide one.

### 5.5 Finding Classification

Nmap service discovery results are not automatically vulnerabilities.

The application must distinguish:

- Discovered host.
- Discovered service.
- Potential security concern.
- Scanner-reported vulnerability.

A service being exposed does not by itself prove that it is vulnerable.

### 5.6 Failure Handling

The adapter must report:

- Scanner unavailable.
- Invalid target.
- Execution failure.
- Timeout.
- Invalid output.
- Partial results.

It must preserve output collected before a failure when possible.

---

## 6. OWASP ZAP Integration

### 6.1 Purpose

OWASP ZAP is used for authorized web application assessment.

The integration should support the configured ZAP capabilities available in the installed environment.

### 6.2 Adapter Responsibilities

The ZAP adapter must:

- Check whether ZAP is available.
- Identify the configured connection method.
- Validate the web application target.
- Expose supported operations.
- Execute approved operations.
- Capture scan status.
- Retrieve available alerts.
- Parse alert evidence.
- Record failures.

### 6.3 Integration Method

The application should use a documented ZAP integration method supported by the installed version.

The implementation may use:
- ZAP API.
- A controlled process invocation.
- Another explicitly configured integration supported by the environment.

The integration method must be selected during implementation.

The adapter must not assume that ZAP is running or that its API is accessible.

### 6.4 Target Restrictions

The adapter must:
- Use the validated web application target.
- Respect the approved scope.
- Prevent unauthorized redirect destinations.
- Apply configured scan restrictions.
- Distinguish passive operations from active testing.

Active testing must require approval when the application's operation policy classifies it as approval-required.

### 6.5 Output Handling

The parser should extract, when available:

- Alert name.
- Alert description.
- Risk level.
- Confidence.
- Affected URL.
- Evidence.
- Solution.
- Reference information.
- CWE identifier.
- CVE identifier, if explicitly provided.

The parser must preserve the original alert information.

### 6.6 Alert Interpretation

A ZAP alert must not automatically be treated as a confirmed exploitable vulnerability.

The agent must consider:
- Alert confidence.
- Evidence.
- Scanner limitations.
- Verification status.

The report must distinguish scanner-reported alerts from independently validated findings.

### 6.7 Failure Handling

The adapter must report:
- ZAP unavailable.
- API connection failure.
- Authentication or configuration failure.
- Scan failure.
- Timeout.
- Invalid alert output.
- Partial results.

The agent must not claim that a ZAP scan completed if the scanner did not report completion.

---

## 7. Nikto Integration

### 7.1 Purpose

Nikto is used for authorized web server checks.

The application should use it to collect relevant web server assessment results.

### 7.2 Adapter Responsibilities

The Nikto adapter must:

- Check whether Nikto is installed.
- Detect its version when possible.
- Validate the target.
- Expose supported operations.
- Execute approved operations.
- Capture output.
- Parse results.
- Record failures.

### 7.3 Target Restrictions

The adapter must:
- Use the validated web target.
- Respect scope restrictions.
- Avoid arbitrary target expansion.
- Reject unsupported target formats.
- Apply the configured operation policy.

### 7.4 Output Handling

The parser should extract, when available:

- Finding description.
- Affected URL.
- HTTP method.
- Relevant response information.
- Reference information.
- Scanner warnings.
- Scanner execution status.

The parser must preserve the original output for traceability.

### 7.5 Finding Interpretation

Nikto results must be treated as scanner-reported observations.

The agent must not automatically conclude that:
- Every reported file is exploitable.
- Every server configuration observation is a vulnerability.
- Every missing security header represents a critical risk.
- Every version disclosure proves that a vulnerable version is running.

The finding's severity must reflect the available evidence.

### 7.6 Failure Handling

The adapter must report:
- Nikto unavailable.
- Invalid target.
- Execution failure.
- Timeout.
- Output parsing failure.
- Partial results.

---

## 8. Common Execution Result

All adapters must return a common execution result.

Suggested model:

```python
class ScannerExecutionResult:
    scanner: str
    operation: str
    target: str
    status: str
    started_at: str
    completed_at: str | None
    duration_seconds: float | None
    raw_output: str
    parsed_output: dict
    findings: list
    error: str | None
```

The actual implementation should use the project's established model conventions.

### Execution Statuses

Suggested statuses:

- Pending
- Running
- Completed
- Failed
- Timed Out
- Cancelled
- Partial

The application must not use Completed when the scanner did not finish successfully.

---

## 9. Finding Normalization

Scanner-specific findings must be converted into a common model.

Suggested fields:

```python
class NormalizedFinding:
    finding_id: str
    assessment_id: str
    title: str
    description: str
    target: str
    affected_url: str | None
    affected_service: str | None
    severity: str | None
    confidence: str | None
    evidence: list
    scanner: str
    scanner_finding_id: str | None
    cve_id: str | None
    cvss_score: float | None
    verification_status: str
    remediation: str | None
    detected_at: str
```

This is a conceptual model.

The implementation must align with the database schema defined in the Backend Schema document.

### Normalization Rules

- Preserve scanner attribution.
- Preserve raw evidence.
- Do not fabricate missing values.
- Keep scanner severity separate from agent priority.
- Keep verification status separate from severity.
- Preserve original finding identifiers when available.
- Allow nullable fields when scanner output does not provide them.

---

## 10. Raw Output Storage

The application must preserve raw scanner output.

Raw output is important for:
- Debugging.
- Re-parsing.
- Evidence review.
- Demonstration.
- Auditability.

The application should store:
- Scanner identifier.
- Operation identifier.
- Target.
- Raw output.
- Execution status.
- Timestamp.
- Parser status.

Raw output must not be replaced by an LLM-generated summary.

The report may display a concise summary, but the original scanner output must remain traceable.

---

## 11. Timeout and Cancellation

Each scanner operation must have a configured timeout.

The timeout must be controlled by application configuration.

The LLM must not be allowed to set unlimited execution time.

When an operation times out:
- Stop or terminate the operation using the adapter's supported method.
- Record the timeout.
- Preserve available output.
- Mark the operation as Timed Out or Partial.
- Do not report successful completion.

Cancellation must prevent new scanner operations from starting.

The application should not claim that a scanner has stopped until the adapter confirms or the process state indicates termination.

---

## 12. Scanner Availability

Scanner availability must be checked before planning execution.

The application should display:

- Scanner name.
- Installed status.
- Version, if available.
- Configuration status.
- Availability error, if applicable.

If a scanner is unavailable:
- Do not select it for execution.
- Explain why it is unavailable.
- Allow the assessment to continue only if the remaining plan is valid.

The agent must not simulate scanner output to compensate for a missing scanner.

---

## 13. Error Handling

Scanner errors must be represented in structured form.

Suggested error categories:

- ScannerNotInstalled
- ScannerUnavailable
- InvalidTarget
- ScopeViolation
- OperationNotAllowed
- ApprovalRequired
- ApprovalRejected
- ExecutionFailed
- ExecutionTimeout
- OutputParseFailed
- Cancelled

Errors must be recorded with the relevant assessment and operation identifiers.

The application should provide a readable error message without losing the underlying diagnostic information.

---

## 14. Security Requirements

Scanner integration must follow these requirements:

1. Scanner execution must occur only through dedicated adapters.
2. Targets must be validated before execution.
3. Scanner operations must be allowlisted.
4. Arbitrary LLM-generated commands must not be executed.
5. Scope restrictions must be enforced by application code.
6. Approval-required operations must not execute before approval.
7. Scanner output must be treated as untrusted data.
8. Scanner output must not be interpreted as instructions to the LLM.
9. Scanner failures must be reported honestly.
10. Assessment records must preserve execution history.

Scanner output may contain misleading text or content designed to manipulate an LLM.

The agent must treat scanner output as assessment data, not as trusted instructions.

---

## 15. Testing Requirements

Each scanner adapter must have tests for:

### Availability

- Scanner installed.
- Scanner missing.
- Scanner version unavailable.
- Scanner configuration invalid.

### Input Validation

- Valid target.
- Invalid target.
- Missing target.
- Target outside scope.
- Unsupported operation.
- Unauthorized operation.

### Execution

- Successful execution.
- Execution failure.
- Timeout.
- Cancellation.
- Partial output.

### Parsing

- Valid scanner output.
- Empty output.
- Malformed output.
- Missing optional fields.
- Unexpected scanner output.

### Finding Normalization

- Correct scanner attribution.
- Correct target.
- Evidence preservation.
- Nullable values.
- Verification state.
- Severity preservation.

### Approval

- Operation permitted without approval.
- Operation requiring approval.
- Approval rejected.
- Approval pending.
- Scope changed after approval.

Tests should use mock scanner outputs where practical.

Real scanner tests should be limited to explicitly authorized local lab targets.

---

## 16. MVP Implementation Order

Implement scanner integration in this order:

### Step 1 — Common Adapter Interface

Create the shared adapter interface and execution result model.

### Step 2 — Nmap Adapter

Implement availability checks, validated execution, structured output capture, and parsing.

### Step 3 — Nikto Adapter

Implement availability checks, controlled execution, output capture, and parsing.

### Step 4 — ZAP Adapter

Implement the configured ZAP integration method, scan status handling, alert retrieval, and parsing.

### Step 5 — Finding Normalization

Convert scanner-specific findings into the common finding model.

### Step 6 — Persistence

Store execution records, raw outputs, and normalized findings.

### Step 7 — Agent Integration

Allow the agent to select only registered scanner operations.

### Step 8 — Approval Enforcement

Add deterministic approval checks immediately before operations that require approval.

### Step 9 — Dashboard Integration

Display scanner availability, execution status, findings, and errors.

### Step 10 — End-to-End Testing

Run the workflow against an authorized local lab target.

---

## 17. MVP Acceptance Criteria

The scanner integration is acceptable when:

1. The application detects scanner availability.
2. Each scanner has a dedicated adapter.
3. The adapters expose predefined operations.
4. Inputs are validated before execution.
5. Scope restrictions are enforced.
6. Approval requirements are enforced.
7. Scanner output is captured.
8. Execution status is recorded.
9. Errors are handled explicitly.
10. Raw output is preserved.
11. Findings are normalized.
12. Evidence remains traceable.
13. The agent cannot execute arbitrary commands.
14. The dashboard accurately reflects scanner execution.
15. The report uses actual scanner results.

---

## 18. Final Design Principle

The scanner integration layer must provide a controlled bridge between the AI agent and the security tools.

**The agent recommends operations. The application validates them. The scanner adapter executes them. The parser preserves evidence. The application records the result.**

This separation makes scanner execution predictable, testable, and auditable.