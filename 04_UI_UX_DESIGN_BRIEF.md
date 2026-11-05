# AI-Powered Unified VAPT Agent
## 04 — UI/UX Design Brief

**Version:** 1.0  
**Status:** Proposed  
**Related documents:** 01_PRD.md, 02_TRD.md, 03_APP_FLOW.md

---

## 1. Purpose

Define the visual design, layout, navigation, interaction patterns, and user experience requirements for the AI-powered Unified VAPT Agent.

The interface shall support the complete assessment workflow:

Assessment Creation → Scope Validation → Plan Review → Scan Execution → Finding Analysis → Approval → Report Generation

The UI must prioritize usability, evidence visibility, assessment status, and analyst control.

---

## 2. Design Goals

The interface shall:

1. Present a professional cybersecurity assessment dashboard.
2. Make assessment progress easy to understand.
3. Clearly distinguish scanner observations from AI-generated analysis.
4. Make findings and supporting evidence accessible.
5. Show scanner failures and limitations.
6. Make approval-required actions explicit.
7. Provide clear report-generation and download actions.
8. Avoid unnecessary complexity for a solo-developer MVP.

The interface shall not imply that a vulnerability is confirmed when the available evidence does not support that conclusion.

---

## 3. Visual Direction

### 3.1 Design Style

Use a professional security-dashboard design.

The interface should feel:

- Clean.
- Technical.
- Structured.
- Readable.
- Consistent.
- Focused on assessment information.

Avoid excessive gradients, decorative animations, oversized cards, and unnecessary visual effects.

### 3.2 Theme

Use a dark cybersecurity dashboard theme.

Recommended design characteristics:

- Dark neutral background.
- Slightly lighter panels.
- High-contrast text.
- Subtle borders.
- Consistent spacing.
- Restrained status colors.

The dark theme is a design preference, not a functional requirement.

### 3.3 Typography

Use a clear, modern sans-serif font.

Typography shall distinguish:

- Page titles.
- Section headings.
- Finding titles.
- Body text.
- Metadata.
- Technical evidence.

Technical evidence may use a monospace font.

### 3.4 Color Semantics

Use colors consistently for status and severity.

Suggested severity mapping:

- Critical: red.
- High: orange.
- Medium: yellow.
- Low: blue.
- Informational: neutral.

Suggested execution states:

- Running: blue.
- Completed: green.
- Failed: red.
- Pending: neutral.
- Approval required: orange.

Color shall not be the only way to communicate status. Labels and icons must also be used.

---

## 4. Application Navigation

Use a persistent sidebar for the primary navigation.

### Navigation Items

1. Dashboard
2. Assessments
3. Findings
4. Reports
5. Integrations

The sidebar shall include:

- Application name.
- Navigation links.
- Current page indicator.
- Optional compact assessment summary.

The main content area shall display the selected page.

The implementation shall remain compatible with the proposed Streamlit application.

---

## 5. Dashboard

### 5.1 Purpose

Provide a high-level overview of assessment activity.

### 5.2 Layout

The dashboard shall contain:

#### Header

- Application title.
- Short description.
- New Assessment action.

#### Summary Metrics

Display:

- Total assessments.
- Running assessments.
- Findings awaiting review.
- Reports generated.

Metrics shall be calculated from persisted application data.

Do not display hardcoded demonstration values as live metrics.

#### Recent Assessments

Display a table containing:

- Assessment name.
- Target.
- Status.
- Finding count.
- Created timestamp.
- Action to open assessment.

#### Scanner Status

Display the current status of the supported scanner integrations.

Each scanner shall indicate whether it is:

- Available.
- Unavailable.
- Not configured.
- Not verified.
- Import-only.

#### Empty State

If no assessments exist:

- Explain that no assessments have been created.
- Provide a New Assessment action.

---

## 6. New Assessment Page

### 6.1 Purpose

Allow the analyst to create an assessment and define its authorized scope.

### 6.2 Form Fields

The page shall include:

- Assessment name.
- Assessment request.
- Target.
- Authorized scope.
- Exclusions.
- Assessment constraints.

Only fields necessary for scope validation and planning should be required.

### 6.3 Actions

Primary action:

**Validate Scope**

The application shall validate the target and scope before generating an executable assessment plan.

### 6.4 Validation Feedback

Display:

- Valid target.
- Invalid target.
- Scope rejected.
- Missing authorization information.
- Excluded target.
- Validation error.

If scope validation fails, show the reason and prevent scan execution.

### 6.5 Successful Validation

After successful scope validation:

- Display the validated target.
- Display authorized scope.
- Display exclusions.
- Provide a Continue to Plan action.

---

## 7. Assessment Plan Review

### 7.1 Purpose

Allow the analyst to inspect the proposed assessment plan before execution.

### 7.2 Layout

Display:

- Assessment name.
- Target.
- Scope.
- Assessment objectives.
- Selected scanners.
- Planned operations.
- Execution sequence.
- Expected outputs.
- Limitations.

### 7.3 Scanner Plan Cards

Each scanner operation shall display:

- Scanner name.
- Operation.
- Purpose.
- Target.
- Reason for selection.
- Expected result.
- Relevant limitations.

The interface shall not display unrestricted shell commands generated by the LLM.

### 7.4 Actions

The analyst may:

- Accept Plan.
- Reject Plan.
- Return to Assessment Configuration.

### 7.5 Plan Acceptance

The application shall record the analyst's decision.

Scan execution shall begin only after plan acceptance.

---

## 8. Assessment Progress Page

### 8.1 Purpose

Provide visibility into scanner execution and assessment processing.

### 8.2 Header

Display:

- Assessment name.
- Target.
- Assessment status.
- Created timestamp.

### 8.3 Progress Overview

Display the current workflow stage:

1. Scope.
2. Planning.
3. Scanning.
4. Processing.
5. Review.
6. Reporting.

The progress indicator shall reflect actual persisted assessment state.

It shall not imply that a stage is complete when it has not completed.

### 8.4 Scanner Execution Table

Display:

- Scanner.
- Operation.
- Status.
- Start time.
- Completion time.
- Result count.
- Error or limitation.

### 8.5 Execution Details

Allow the analyst to inspect:

- Scanner version.
- Execution status.
- Target.
- Original output reference.
- Error details.
- Execution timestamps.

### 8.6 Failure Display

Failed and timed-out scans shall be clearly identified.

The interface shall distinguish:

- Scanner failure.
- Timeout.
- Unsupported operation.
- Successful execution with no findings.

---

## 9. Findings Page

### 9.1 Purpose

Allow the analyst to review normalized findings, risk priorities, and evidence.

### 9.2 Findings Summary

Display:

- Total findings.
- Findings by severity.
- Findings by validation status.
- Findings requiring review.

Metrics shall be derived from assessment data.

### 9.3 Findings Table

Each row shall display:

- Finding title.
- Severity.
- Affected asset.
- Source scanner.
- Confidence.
- Validation status.
- Risk priority.

The table shall support sorting and filtering where practical.

### 9.4 Filters

Provide filters for:

- Severity.
- Scanner.
- Asset.
- Confidence.
- Validation status.
- Finding category.

### 9.5 Finding Details

Selecting a finding shall open a detail view.

Display:

#### Overview

- Finding identifier.
- Title.
- Description.
- Severity.
- Affected asset.
- Category.
- Confidence.
- Validation status.

#### Risk Analysis

- Risk explanation.
- Available severity/CVSS information.
- Exposure.
- Exploitability.
- Asset impact.
- Confidence considerations.

Only available and supported values shall be displayed.

#### Evidence

Display:

- Source scanner.
- Source finding identifier.
- Evidence description.
- Original output reference.
- Timestamp.
- Relevant technical details.

#### Remediation

Display:

- Recommended remediation.
- Supporting references.
- Remediation limitations.

#### Correlation

If findings have been merged:

- Display contributing scanner findings.
- Display correlation rationale.
- Preserve each source reference.
- Display evidence from each source.

If correlation is uncertain, display that uncertainty.

---

## 10. Human Approval Interface

### 10.1 Purpose

Provide explicit analyst control over active validation and offensive actions.

### 10.2 Approval Request

Display:

- Finding.
- Target.
- Proposed validation action.
- Purpose.
- Expected evidence.
- Potential impact.
- Scope constraints.
- Reason for validation.

### 10.3 Decision Controls

Provide:

- Approve.
- Reject.
- Defer.

The decision shall require an explicit analyst action.

The interface shall not automatically approve a proposal.

### 10.4 Approval Status

Display:

- Pending.
- Approved.
- Rejected.
- Deferred.
- Executed.
- Execution failed.
- Cancelled.

### 10.5 Audit Information

Display:

- Decision.
- Analyst.
- Decision timestamp.
- Execution status.
- Outcome.

The interface shall clearly distinguish approval from execution.

---

## 11. Reports Page

### 11.1 Purpose

Allow analysts to generate and access assessment reports.

### 11.2 Report Summary

Display:

- Assessment name.
- Target.
- Report status.
- Generated timestamp.
- Finding count.
- Report availability.

### 11.3 Report Generation

Provide a Generate Report action.

During generation, display the actual report-generation state.

If generation fails, display the failure and allow retry.

### 11.4 Download

When a report exists, provide a Download PDF action.

The report shall be generated from persisted assessment data.

### 11.5 Report Preview

Where practical, display a summary containing:

- Executive summary.
- Scope.
- Severity distribution.
- Key findings.
- Limitations.

The PDF remains the downloadable report artifact.

---

## 12. Scanner Integrations Page

### 12.1 Purpose

Display scanner availability and integration verification status.

### 12.2 Scanner Cards

Each scanner shall display:

- Scanner name.
- Scanner category.
- Execution mode.
- Availability.
- Verification status.
- Version, when available.
- Configuration status.

### 12.3 Initial Scanner List

- Nmap.
- OWASP ZAP.
- Nikto.

### 12.4 Integration Status

Display one of:

- Verified.
- Installed, not verified.
- Configured, not verified.
- Unavailable.
- Import-only.
- Planned.

The application shall not label an integration verified until its execution or import workflow has been tested successfully.

---

## 13. Interaction and Feedback Requirements

The interface shall:

- Show loading states for ongoing operations.
- Show success messages only after successful completion.
- Show errors clearly.
- Preserve user-entered assessment data when practical.
- Prevent duplicate submissions where appropriate.
- Confirm consequential actions.
- Distinguish pending operations from completed operations.
- Provide clear navigation back to the assessment.

The interface shall not claim that an operation succeeded before receiving its result.

---

## 14. Responsive Layout

The initial MVP shall prioritize desktop use.

The layout shall:

- Use a persistent sidebar.
- Keep tables readable.
- Avoid horizontal overflow where practical.
- Support reasonable browser resizing.
- Keep primary actions visible.
- Allow evidence and technical details to be inspected without excessive navigation.

Mobile-specific optimization is not a mandatory MVP requirement.

---

## 15. Accessibility and Readability

The application shall:

- Use readable text sizes.
- Maintain adequate contrast.
- Avoid color-only status indicators.
- Label interactive controls.
- Provide meaningful error messages.
- Keep technical evidence selectable and readable.
- Avoid unnecessary animation.

---

## 16. UI Acceptance Criteria

The UI is acceptable when:

1. An analyst can create an assessment.
2. Scope validation feedback is visible.
3. The assessment plan can be reviewed.
4. Scanner execution progress is visible.
5. Scanner failures are clearly displayed.
6. Findings can be filtered and inspected.
7. Evidence and source references are accessible.
8. Approval requests are explicit.
9. Approval decisions are recorded and displayed.
10. Report generation status is visible.
11. A generated PDF can be downloaded.
12. Integration verification status is accurately represented.

---

## 17. Implementation Constraints

The interface shall use Streamlit for the initial MVP.

The design shall avoid requiring:

- A separate frontend framework.
- A separate authentication service.
- Complex multi-page frontend routing.
- Unnecessary animation libraries.
- Unnecessary UI component libraries.

Additional dependencies require an explicit implementation justification.

---

## 18. Relationship to Other Documents

This document defines UI/UX behavior.

The remaining documents shall define:

- 05_BACKEND_SCHEMA.md — data structures.
- 06_IMPLEMENTATION_PLAN.md — implementation sequence.
- 07_AGENT_BEHAVIOR.md — agent planning and reasoning.
- 08_TOOL_CONTRACTS.md — scanner interfaces.
- 09_SAFETY_RULES.md — enforced safety boundaries.

The interface shall not introduce functionality that contradicts the PRD, TRD, or application flow.
