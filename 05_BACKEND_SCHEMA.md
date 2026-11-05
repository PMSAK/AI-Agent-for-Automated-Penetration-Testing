# AI-Powered Unified VAPT Agent
## 05 — Backend Schema

**Version:** 1.0  
**Status:** Proposed  
**Database:** SQLite  
**Related documents:** 01_PRD.md, 02_TRD.md, 03_APP_FLOW.md, 04_UI_UX_DESIGN_BRIEF.md

---

## 1. Purpose

This document defines the persistent data model for the AI-powered Unified VAPT Agent.

The schema shall support:

- Assessment creation and lifecycle tracking.
- Authorized assessment scope.
- Assessment planning.
- Scanner execution tracking.
- Asset discovery.
- Finding normalization.
- Finding correlation.
- Evidence preservation.
- Risk prioritization.
- Human approval.
- Report generation.
- Auditability.

The schema must support the application workflows defined in 03_APP_FLOW.md.

---

## 2. Database Technology

The initial implementation shall use SQLite.

### Requirements

- Use relational tables.
- Use primary keys for persistent entities.
- Use foreign keys to maintain relationships.
- Store timestamps in a consistent UTC representation.
- Use JSON text for structured fields that do not require relational querying.
- Preserve scanner-native identifiers.
- Avoid storing duplicate copies of large scanner outputs unnecessarily.
- Use database transactions for related updates.
- Enable SQLite foreign-key enforcement.

SQLite shall be accessed through the application's persistence layer.

The implementation shall not allow UI components, scanner adapters, or LLM code to independently modify database records without using the persistence layer.

---

## 3. Entity Overview

The database shall contain the following primary entities:

1. Assessment
2. AssessmentScope
3. AssessmentPlan
4. Asset
5. ScannerExecution
6. Finding
7. FindingSource
8. Evidence
9. FindingCorrelation
10. Approval
11. Report
12. AuditEvent

### Relationships

- An assessment has one scope record.
- An assessment may have multiple plans.
- An assessment may contain multiple assets.
- An assessment may contain multiple scanner executions.
- An assessment may contain multiple findings.
- A scanner execution may produce multiple findings.
- A finding may have multiple source scanner records.
- A finding may reference multiple evidence records.
- A finding may participate in correlation records.
- A finding may have multiple approval records.
- An assessment may have multiple report records.
- An assessment may have multiple audit events.

All assessment-related records shall reference their owning assessment.

---

## 4. Entity: Assessment

### Purpose

Stores the assessment's identity, request, lifecycle state, and summary information.

### Table: `assessments`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Assessment UUID |
| `name` | TEXT | NOT NULL | Assessment name |
| `request` | TEXT | NOT NULL | Original assessment request |
| `target` | TEXT | NOT NULL | Primary requested target |
| `status` | TEXT | NOT NULL | Assessment lifecycle state |
| `created_at` | TEXT | NOT NULL | Creation timestamp |
| `updated_at` | TEXT | NOT NULL | Last update timestamp |
| `started_at` | TEXT | Nullable | Assessment start timestamp |
| `completed_at` | TEXT | Nullable | Assessment completion timestamp |
| `created_by` | TEXT | Nullable | Analyst identifier, if available |
| `summary` | TEXT | Nullable | Evidence-grounded assessment summary |

### Constraints

- `id` shall be unique.
- `name`, `request`, and `target` shall not be empty.
- `status` shall use an approved assessment state.
- `completed_at` shall remain NULL until completion.
- Summary content shall not contain fabricated findings.

### Assessment Status Values

- `created`
- `scope_pending`
- `scope_rejected`
- `planning`
- `plan_pending_review`
- `plan_rejected`
- `ready`
- `running`
- `processing_results`
- `review_pending`
- `approval_pending`
- `reporting`
- `completed`
- `completed_with_limitations`
- `failed`
- `cancelled`

The application shall validate state transitions.

---

## 5. Entity: Assessment Scope

### Purpose

Stores the authorization boundaries and target restrictions for an assessment.

### Table: `assessment_scopes`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Scope UUID |
| `assessment_id` | TEXT | NOT NULL, UNIQUE, FK | Owning assessment |
| `scope_definition` | TEXT | NOT NULL | Structured authorized scope |
| `exclusions` | TEXT | NOT NULL | Structured excluded targets |
| `authorization_reference` | TEXT | Nullable | Reference to authorization information |
| `validation_status` | TEXT | NOT NULL | Scope validation outcome |
| `validation_details` | TEXT | Nullable | Validation explanation |
| `validated_at` | TEXT | Nullable | Validation timestamp |
| `created_at` | TEXT | NOT NULL | Creation timestamp |

### Validation Status Values

- `pending`
- `validated`
- `rejected`
- `requires_review`

### Requirements

- Scope shall be associated with exactly one assessment.
- Exclusions shall be preserved.
- Scope validation shall be performed by deterministic application logic.
- Scanner execution shall require validated scope.
- Scope changes shall invalidate prior approval where the change affects the approved operation.
- The LLM shall not modify or override authorization state.

---

## 6. Entity: Assessment Plan

### Purpose

Stores the structured assessment plan generated by the agent and the analyst's review decision.

### Table: `assessment_plans`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Plan UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `version` | INTEGER | NOT NULL | Plan version |
| `plan_data` | TEXT | NOT NULL | Structured plan JSON |
| `reasoning_summary` | TEXT | Nullable | Plan explanation |
| `status` | TEXT | NOT NULL | Plan review status |
| `created_at` | TEXT | NOT NULL | Plan creation timestamp |
| `reviewed_at` | TEXT | Nullable | Analyst review timestamp |
| `reviewed_by` | TEXT | Nullable | Analyst identifier |
| `review_comment` | TEXT | Nullable | Review comment |

### Constraints

- Plan versions shall be unique within an assessment.
- Plan data shall be validated against the expected schema.
- Only accepted plans may authorize scanner execution.
- Rejected plans shall not authorize scanner execution.
- Changes to a plan shall create a new version rather than silently overwrite an accepted plan.

### Plan Status Values

- `pending_review`
- `accepted`
- `rejected`
- `superseded`

---

## 7. Entity: Asset

### Purpose

Stores discovered or assessed hosts, services, URLs, and other relevant targets.

### Table: `assets`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Asset UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `asset_type` | TEXT | NOT NULL | Asset category |
| `value` | TEXT | NOT NULL | Host, IP, URL, or service identifier |
| `hostname` | TEXT | Nullable | Hostname |
| `ip_address` | TEXT | Nullable | IP address |
| `port` | INTEGER | Nullable | Network port |
| `protocol` | TEXT | Nullable | Protocol |
| `service_name` | TEXT | Nullable | Detected service |
| `description` | TEXT | Nullable | Asset description |
| `discovery_source` | TEXT | Nullable | Scanner or discovery source |
| `first_seen_at` | TEXT | NOT NULL | First observation |
| `last_seen_at` | TEXT | NOT NULL | Latest observation |

### Asset Type Values

- `host`
- `ip`
- `url`
- `service`
- `other`

### Requirements

- Assets shall belong to an assessment.
- Asset values shall be normalized consistently.
- Different services on the same host shall remain distinguishable.
- Asset discovery shall not imply authorization to scan the discovered asset.
- Newly discovered assets shall be checked against scope before further scanning.

---

## 8. Entity: Scanner Execution

### Purpose

Tracks each scanner operation independently.

### Table: `scanner_executions`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Execution UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `plan_id` | TEXT | Nullable, FK | Accepted plan |
| `asset_id` | TEXT | Nullable, FK | Target asset |
| `scanner_name` | TEXT | NOT NULL | Scanner identifier |
| `scanner_version` | TEXT | Nullable | Scanner version |
| `operation` | TEXT | NOT NULL | Approved operation |
| `status` | TEXT | NOT NULL | Execution state |
| `target` | TEXT | NOT NULL | Execution target |
| `input_data` | TEXT | Nullable | Validated execution parameters |
| `output_reference` | TEXT | Nullable | Original output reference |
| `error_message` | TEXT | Nullable | Execution error |
| `exit_code` | INTEGER | Nullable | Process exit code |
| `started_at` | TEXT | Nullable | Start timestamp |
| `completed_at` | TEXT | Nullable | Completion timestamp |
| `created_at` | TEXT | NOT NULL | Record creation timestamp |

### Execution Status Values

- `queued`
- `running`
- `completed`
- `failed`
- `timed_out`
- `cancelled`

### Requirements

- Each scanner operation shall have its own execution record.
- Scanner failures shall not be represented as successful executions.
- Original output shall be preserved or referenced.
- Scanner inputs shall be validated before execution.
- Execution records shall identify the scanner and operation.
- Execution status shall reflect the actual outcome.

---

## 9. Entity: Finding

### Purpose

Stores normalized vulnerability and security finding information.

### Table: `findings`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Finding UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `asset_id` | TEXT | Nullable, FK | Affected asset |
| `title` | TEXT | NOT NULL | Finding title |
| `description` | TEXT | NOT NULL | Finding description |
| `category` | TEXT | Nullable | Finding category |
| `severity` | TEXT | NOT NULL | Normalized severity |
| `cvss_score` | REAL | Nullable | CVSS score, if available |
| `cvss_vector` | TEXT | Nullable | CVSS vector, if available |
| `cve_id` | TEXT | Nullable | CVE reference |
| `cwe_id` | TEXT | Nullable | CWE reference |
| `confidence` | TEXT | NOT NULL | Confidence level |
| `validation_status` | TEXT | NOT NULL | Finding validation state |
| `risk_score` | REAL | Nullable | Calculated risk score |
| `risk_explanation` | TEXT | Nullable | Risk explanation |
| `remediation` | TEXT | Nullable | Remediation recommendation |
| `correlation_group_id` | TEXT | Nullable | Correlation group reference |
| `created_at` | TEXT | NOT NULL | Creation timestamp |
| `updated_at` | TEXT | NOT NULL | Last update timestamp |

### Severity Values

- `critical`
- `high`
- `medium`
- `low`
- `informational`
- `unknown`

### Confidence Values

- `high`
- `medium`
- `low`
- `unknown`

### Validation Status Values

- `unverified`
- `scanner_observed`
- `validated`
- `false_positive`
- `inconclusive`

### Requirements

- Findings shall belong to an assessment.
- A finding may reference an asset.
- Missing CVE, CWE, CVSS, or confidence information shall remain unknown.
- Scanner-observed findings shall not automatically be marked validated.
- AI-generated descriptions and recommendations shall not replace original scanner evidence.
- Risk scores shall be reproducible from recorded inputs and the documented risk method.
- A finding shall not be marked false positive without a recorded basis.

---

## 10. Entity: Finding Source

### Purpose

Preserves the relationship between a normalized finding and its original scanner observations.

### Table: `finding_sources`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Source UUID |
| `finding_id` | TEXT | NOT NULL, FK | Normalized finding |
| `scanner_execution_id` | TEXT | NOT NULL, FK | Scanner execution |
| `source_finding_id` | TEXT | Nullable | Scanner-native finding identifier |
| `source_title` | TEXT | Nullable | Original title |
| `source_severity` | TEXT | Nullable | Original severity |
| `source_data` | TEXT | Nullable | Relevant scanner-native data |
| `created_at` | TEXT | NOT NULL | Creation timestamp |

### Constraints

- A source record shall reference a finding.
- A source record shall reference a scanner execution.
- The same scanner-native finding shall not be duplicated within the same execution.
- Source information shall remain available after correlation.

### Unique Constraint

`scanner_execution_id + source_finding_id`

When a scanner does not provide a stable finding identifier, the parser shall use a documented fallback identity.

---

## 11. Entity: Evidence

### Purpose

Stores evidence references associated with findings.

### Table: `evidence`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Evidence UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `finding_id` | TEXT | Nullable, FK | Associated finding |
| `scanner_execution_id` | TEXT | Nullable, FK | Source execution |
| `evidence_type` | TEXT | NOT NULL | Evidence category |
| `description` | TEXT | Nullable | Evidence description |
| `content_reference` | TEXT | Nullable | Stored file or output reference |
| `content_hash` | TEXT | Nullable | Integrity hash |
| `source_location` | TEXT | Nullable | Scanner output location |
| `captured_at` | TEXT | NOT NULL | Capture timestamp |
| `metadata` | TEXT | Nullable | Structured metadata |

### Evidence Type Values

- `scanner_output`
- `http_request`
- `http_response`
- `service_banner`
- `screenshot`
- `log`
- `other`

### Requirements

- Evidence shall belong to an assessment.
- Evidence shall reference its source when available.
- Evidence shall not be fabricated by the LLM.
- Large evidence content may be stored as a file, with the database retaining a reference.
- Evidence integrity shall be supported through content hashing where applicable.
- Sensitive evidence shall not be included in reports unless appropriate for the assessment.

---

## 12. Entity: Finding Correlation

### Purpose

Stores correlation decisions between findings.

### Table: `finding_correlations`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Correlation UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `finding_id` | TEXT | NOT NULL, FK | First finding |
| `related_finding_id` | TEXT | NOT NULL, FK | Related finding |
| `relationship_type` | TEXT | NOT NULL | Relationship classification |
| `confidence` | TEXT | NOT NULL | Correlation confidence |
| `reason` | TEXT | Nullable | Correlation explanation |
| `created_at` | TEXT | NOT NULL | Creation timestamp |

### Relationship Type Values

- `duplicate`
- `related`
- `potential_duplicate`

### Requirements

- Findings shall not be correlated across different assessments.
- A finding shall not be correlated with itself.
- Correlation shall preserve both findings and their source evidence.
- Uncertain correlations shall not automatically merge findings.
- Correlation rationale shall be retained.

---

## 13. Entity: Approval

### Purpose

Records analyst decisions for proposed active validation actions.

### Table: `approvals`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Approval UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `finding_id` | TEXT | Nullable, FK | Related finding |
| `plan_id` | TEXT | Nullable, FK | Related plan |
| `proposed_action` | TEXT | NOT NULL | Structured action proposal |
| `purpose` | TEXT | NOT NULL | Reason for action |
| `potential_impact` | TEXT | Nullable | Potential impact |
| `scope_snapshot` | TEXT | NOT NULL | Scope at proposal time |
| `status` | TEXT | NOT NULL | Approval state |
| `decision` | TEXT | Nullable | Analyst decision |
| `decision_by` | TEXT | Nullable | Analyst identifier |
| `decision_at` | TEXT | Nullable | Decision timestamp |
| `decision_comment` | TEXT | Nullable | Analyst comment |
| `execution_id` | TEXT | Nullable, FK | Resulting execution |
| `created_at` | TEXT | NOT NULL | Proposal timestamp |

### Approval Status Values

- `pending`
- `approved`
- `rejected`
- `deferred`
- `executed`
- `execution_failed`
- `cancelled`

### Requirements

- Approval shall be associated with an assessment.
- The proposed action shall be structured and inspectable.
- Approval shall be explicit.
- The LLM shall not create an approval decision.
- The scope snapshot shall be preserved.
- Execution shall reference the relevant approval.
- An approved action shall not be considered executed until execution outcome is recorded.
- A change in relevant scope shall invalidate the approval.

---

## 14. Entity: Report

### Purpose

Tracks generated assessment reports.

### Table: `reports`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Report UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `report_type` | TEXT | NOT NULL | Report category |
| `status` | TEXT | NOT NULL | Report generation state |
| `file_reference` | TEXT | Nullable | PDF file reference |
| `content_hash` | TEXT | Nullable | Report integrity hash |
| `generated_at` | TEXT | Nullable | Successful generation timestamp |
| `generated_by` | TEXT | Nullable | Analyst or system identifier |
| `error_message` | TEXT | Nullable | Generation error |
| `created_at` | TEXT | NOT NULL | Record creation timestamp |

### Report Status Values

- `queued`
- `generating`
- `completed`
- `failed`

### Requirements

- A report shall belong to an assessment.
- A completed report shall have a valid file reference.
- Failed report generation shall be recorded.
- Reports shall be generated from persisted assessment data.
- The report shall disclose scanner failures and assessment limitations.
- Report content shall not invent findings.

---

## 15. Entity: Audit Event

### Purpose

Provides an audit trail for significant assessment actions.

### Table: `audit_events`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | Primary key | Event UUID |
| `assessment_id` | TEXT | NOT NULL, FK | Owning assessment |
| `event_type` | TEXT | NOT NULL | Event classification |
| `actor_type` | TEXT | NOT NULL | User, system, or scanner |
| `actor_id` | TEXT | Nullable | Actor identifier |
| `entity_type` | TEXT | Nullable | Related entity type |
| `entity_id` | TEXT | Nullable | Related entity identifier |
| `event_data` | TEXT | Nullable | Structured event details |
| `created_at` | TEXT | NOT NULL | Event timestamp |

### Requirements

- Audit events shall belong to an assessment.
- Events shall identify the action and relevant entity.
- Approval decisions shall be auditable.
- Scanner execution outcomes shall be auditable.
- Events shall not contain API keys or unnecessary sensitive data.
- Audit events shall not be silently overwritten during normal application operation.

---

## 16. Relationships and Referential Integrity

The database shall enforce foreign-key relationships.

### Required Relationships

- `assessment_scopes.assessment_id` → `assessments.id`
- `assessment_plans.assessment_id` → `assessments.id`
- `assets.assessment_id` → `assessments.id`
- `scanner_executions.assessment_id` → `assessments.id`
- `scanner_executions.plan_id` → `assessment_plans.id`
- `scanner_executions.asset_id` → `assets.id`
- `findings.assessment_id` → `assessments.id`
- `findings.asset_id` → `assets.id`
- `finding_sources.finding_id` → `findings.id`
- `finding_sources.scanner_execution_id` → `scanner_executions.id`
- `evidence.assessment_id` → `assessments.id`
- `evidence.finding_id` → `findings.id`
- `evidence.scanner_execution_id` → `scanner_executions.id`
- `finding_correlations.assessment_id` → `assessments.id`
- `finding_correlations.finding_id` → `findings.id`
- `finding_correlations.related_finding_id` → `findings.id`
- `approvals.assessment_id` → `assessments.id`
- `approvals.finding_id` → `findings.id`
- `approvals.plan_id` → `assessment_plans.id`
- `approvals.execution_id` → `scanner_executions.id`
- `reports.assessment_id` → `assessments.id`
- `audit_events.assessment_id` → `assessments.id`

The application shall verify that related records belong to the same assessment before creating cross-entity relationships.

---

## 17. Indexing

The following indexes shall be considered for the MVP:

- `assessments.status`
- `assessments.created_at`
- `assets.assessment_id`
- `assets.value`
- `scanner_executions.assessment_id`
- `scanner_executions.status`
- `findings.assessment_id`
- `findings.asset_id`
- `findings.severity`
- `findings.validation_status`
- `finding_sources.finding_id`
- `finding_sources.scanner_execution_id`
- `evidence.finding_id`
- `finding_correlations.assessment_id`
- `approvals.assessment_id`
- `approvals.status`
- `reports.assessment_id`
- `audit_events.assessment_id`
- `audit_events.created_at`

Indexes shall be added only where useful for actual application queries.

---

## 18. Data Validation

The persistence layer shall validate:

- Required fields.
- UUID format.
- Assessment state values.
- Scanner execution state values.
- Finding severity values.
- Confidence values.
- Validation status values.
- Approval status values.
- Report status values.
- Foreign-key relationships.
- Structured JSON fields.

Invalid records shall be rejected rather than silently accepted.

The database shall not rely on the LLM to validate data integrity.

---

## 19. Data Lifecycle

### Assessment Creation

Create the assessment and its scope record.

### Planning

Create a plan record with a version number.

### Execution

Create one execution record per scanner operation.

### Result Processing

Create assets, findings, finding-source records, and evidence records.

### Correlation

Create correlation records while preserving original findings.

### Approval

Create approval records for proposed active validation.

### Reporting

Create a report record and update its status as generation progresses.

### Completion

Update the assessment state based on actual execution and reporting outcomes.

---

## 20. Implementation Constraints

The initial implementation shall:

- Use SQLite.
- Use UUID identifiers.
- Use UTC timestamps.
- Use foreign keys.
- Use structured JSON where appropriate.
- Keep persistence logic separate from UI logic.
- Keep scanner-specific parsing separate from database operations.
- Avoid unnecessary database abstraction frameworks.
- Avoid unnecessary tables that do not support the MVP.

The schema may be refined during implementation, but changes shall remain consistent with the PRD, TRD, and application flow.

---

## 21. Schema Acceptance Criteria

The schema is acceptable when:

1. An assessment can be created and retrieved.
2. Scope validation is persisted.
3. Assessment plans and review decisions are persisted.
4. Scanner executions are tracked independently.
5. Assets can be associated with assessments.
6. Findings can be normalized and stored.
7. Findings retain their original scanner sources.
8. Evidence can be associated with findings and executions.
9. Correlation decisions preserve original findings.
10. Approval proposals and decisions are persisted.
11. Reports and their generation status are persisted.
12. Audit events can be retrieved.
13. Foreign-key integrity is enforced.
14. Invalid state values are rejected.
15. Assessment data can be retrieved to generate a traceable report.

---

## 22. Relationship to Other Documents

This document defines the persistent data model.

The remaining documents shall define:

- 06_IMPLEMENTATION_PLAN.md — implementation milestones and dependencies.
- 07_AGENT_BEHAVIOR.md — agent planning and reasoning.
- 08_TOOL_CONTRACTS.md — scanner adapter interfaces.
- 09_SAFETY_RULES.md — scope and execution restrictions.

The implementation shall not introduce data structures that conflict with this schema without documenting and reviewing the change.
