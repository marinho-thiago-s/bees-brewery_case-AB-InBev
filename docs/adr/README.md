# Architecture Decision Records (ADRs)

Status: Complete
Last Updated: 2026-02-02

---

## What are ADRs?

ADRs (Architecture Decision Records) document important architectural decisions, their context, considered alternatives and consequences. This helps:

- Understand WHY each decision was made
- Avoid re-deciding the same thing in the future
- Onboard new developers quickly
- Track architectural evolution

---

## Project ADRs

### ADR-001: Modular and Scalable Data Pipeline Architecture

**Status:** Accepted
**Date:** 2026-02-01
**Covers:** Architectural layers, separation of concerns, design patterns

**Decision:** Implement layered architecture (Orchestration -> Jobs -> Services -> Config -> Data)

**Why:**
- Scalability: Add new jobs without breaking existing code
- Testability: Abstract dependencies (storage, spark) for mocks
- Maintainability: Each layer has clear responsibility

**Alternatives rejected:**
- Monolithic script (not scalable, difficult to test)
- Serverless/Lambda (15min timeout inadequate)
- Beam/Dataflow (overkill for batch, vendor lock-in)

**Impact:** Fundamental to architecture, enables growth

---

### ADR-002: Technology Stack and Implementation Details

**Status:** Accepted
**Date:** 2026-02-01
**Covers:** PySpark, Airflow, Parquet, Docker, Exception handling

**Key Decisions:**

| Component | Technology | Alternative | Reason |
|-----------|-----------|------------|--------|
| Data Layer | Medallion (3 layers) | Single layer | Auditability + separation |
| Processing | Apache Spark | Pandas/Dask/Polars | Native partitioning + maturity |
| Orchestration | Apache Airflow | Prefect/Dagster/Cron | Superior UI + community |
| Storage Format | Parquet | CSV/JSON/ORC | Columnar + compression + partitioning |
| Error Handling | Exception hierarchy | Flat exceptions | Type-specific handling |
| Deployment | Docker | Virtual envs | Reproducible + cloud-native |

**Impact:** Defines all project tools

---

### ADR-003: Medallion Pattern Implementation

**Status:** Implemented
**Date:** 2026-02-02

**Decision:** Implement Medallion with 3 explicit layers (Bronze -> Silver -> Gold)

**Layers:**
- Bronze: Raw data (9.083 raw records)
- Silver: Cleaned (5.451 records, 60% retention)
- Gold: Analytics-ready (389 aggregations)

**Benefits:**
- Complete auditability (Bronze = exact source copy)
- Scalability (each layer independent)
- Data quality (validations applied at each layer)

---

## Using ADRs

### For Developers

1. Read ADR-001 to understand general architecture
2. Read ADR-002 to understand technologies
3. Read ADR-003 to understand data flow
4. When implementing something new, check for relevant ADR

### For Architects

1. When making important decision, create new ADR
2. Reference related existing ADRs
3. Document considered alternatives
4. Keep status and date clear

### For New Team Members

1. Start with this README
2. Read ADR-001 (how everything is organized)
3. Read ADR-002 (why we use these technologies)
4. Explore code with architecture context

---

## ADR Template

Each ADR follows this structure:

```markdown
# ADR-XXX: Decision Title

## Context
What led us to this decision?
(business requirements, technical constraints, etc)

## Decision
What did we decide?

## Rationale
Why? (with comparison of alternatives)

## Consequences
Positive impacts and trade-offs

## Alternatives Considered
Rejected options and reasons
```

---

## Future ADRs (Planned)

When we implement these topics:

- ADR-004: S3 Storage Backend Integration
- ADR-005: Kubernetes Deployment Strategy
- ADR-006: Delta Lake for ACID Transactions
- ADR-007: Data Catalog Implementation
- ADR-008: ML Pipeline Integration

---

## References

- Michael Nygard: Architecture Decision Records
- ADR GitHub
- ADR Tools

---

Next Review: 2026-03-01
Maintained by: Data Engineering Team
