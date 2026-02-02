# 📋 Architecture Decision Records (ADRs)

**Status:** ✅ Complete  
**Last Updated:** 2026-02-02

---

## O que são ADRs?

ADRs (Architecture Decision Records) documentam decisões arquiteturais importantes, seu contexto, alternativas consideradas e consequências. Isto facilita:

- ✅ Entender POR QUE cada decisão foi tomada
- ✅ Evitar re-decidir a mesma coisa no futuro
- ✅ Onboard novos desenvolvedores rapidamente
- ✅ Rastrear evolução arquitetural

---

## ADRs do Projeto

### ✅ [ADR-001: Modular and Scalable Data Pipeline Architecture](ADR-001-modular-architecture.md)

**Status:** Accepted  
**Date:** 2026-02-01  
**Covers:** Architectural layers, separation of concerns, design patterns

**Decisão:** Implementar arquitetura em camadas (Orchestration → Jobs → Services → Config → Data)

**Por quê:**
- Escalabilidade: Adicionar novos jobs sem quebrar código existente
- Testabilidade: Abstrair dependências (storage, spark) para mocks
- Manutenibilidade: Cada layer tem responsabilidade clara

**Alternativas rejeitadas:**
- ❌ Monolithic script (não escalável, difícil testar)
- ❌ Serverless/Lambda (15min timeout inadequado)
- ❌ Beam/Dataflow (overkill para batch, vendor lock-in)

**Impacto:** Fundamental à arquitetura, permite crescimento

---

### ✅ [ADR-002: Technology Stack & Implementation Details](ADR-002-TECH-STACK.md)

**Status:** Accepted  
**Date:** 2026-02-01  
**Covers:** PySpark, Airflow, Parquet, Docker, Exception handling

**Decisões Principais:**

| Componente | Tecnologia | Alternativa Rejeitada | Motivo |
|-----------|-----------|----------------------|--------|
| Data Layer | Medallion (3 layers) | Single layer | Auditabilidade + separação |
| Processing | Apache Spark | Pandas/Dask/Polars | Partitioning nativo + maturity |
| Orchestration | Apache Airflow | Prefect/Dagster/Cron | Superior UI + comunidade |
| Storage Format | Parquet | CSV/JSON/ORC | Columnar + compression + partitioning |
| Error Handling | Exception hierarchy | Flat exceptions | Type-specific handling |
| Deployment | Docker | Virtual envs | Reproducible + cloud-native |

**Impacto:** Define todas as ferramentas do projeto

---

### 📌 ADR-003: Medallion Pattern Implementation

**Status:** Post-implementation documentation  
**Date:** 2026-02-02

**Decisão:** Implementar Medallion com 3 camadas explícitas (Bronze → Silver → Gold)

**Camadas:**
- **Bronze:** Raw data (9.083 registros brutos)
- **Silver:** Cleaned (5.451 registros, 60% retenção)
- **Gold:** Analytics-ready (389 agregações)

**Benefícios:**
- ✅ Auditabilidade completa (Bronze = cópia exata da fonte)
- ✅ Escalabilidade (cada camada independente)
- ✅ Data quality (validações aplicadas em cada camada)

---

## Estrutura de um ADR

Cada ADR segue este template:

```markdown
# ADR-XXX: Título da Decisão

## Context
O que nos levou a esta decisão?
(business requirements, technical constraints, etc)

## Decision
O que decidimos?

## Rationale
Por quê? (com comparação de alternativas)

## Consequences
Impactos positivos e trade-offs

## Alternatives Considered
Opções rejeitadas e motivos
```

---

## Como Usar ADRs

### Para Developers
```
1. Leia ADR-001 para entender a arquitetura geral
2. Leia ADR-002 para entender as tecnologias
3. Leia ADR-003 para entender o fluxo de dados
4. Ao implementar algo novo, veja se existe ADR relevante
```

### Para Arquitetos
```
1. Quando tomar decisão importante, crie novo ADR
2. Referencie ADRs existentes relacionados
3. Documente alternativas consideradas
4. Deixe o status e data clara
```

### Para Novos Membros do Time
```
1. Comece com este README
2. Leia ADR-001 (como tudo é organizado)
3. Leia ADR-002 (por que usamos essas tecnologias)
4. Explore o código com contexto da arquitetura
```

---

## Evolução Futura (ADRs Planejados)

Quando implementarmos estes tópicos:

- [ ] **ADR-004:** S3 Storage Backend Integration
- [ ] **ADR-005:** Kubernetes Deployment Strategy
- [ ] **ADR-006:** Delta Lake for ACID Transactions
- [ ] **ADR-007:** Data Catalog Implementation
- [ ] **ADR-008:** ML Pipeline Integration

---

## Referências

- [Michael Nygard: ADRs](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR GitHub](https://adr.github.io/)
- [ADR Tools](https://github.com/npryce/adr-tools)

---

**Next Review:** 2026-03-01  
**Maintained by:** Data Engineering Team
