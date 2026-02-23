# Global News Attention Tracker

**Tool Name:** Global News Attention Tracker — Transforms Guardian API article data into geographic coverage reports showing which countries dominate news attention.

---

## Process Diagram

```mermaid
flowchart LR
    subgraph Input
        A[Guardian API<br>Article Data]
    end

    subgraph Processing
        B[SUMMARIZE<br>Aggregate counts<br>by country]
        C[INTERPRET<br>Rank coverage,<br>calculate per-capita,<br>categorize topics]
        D[FORMAT<br>Generate charts,<br>tables, statistics]
    end

    subgraph Output
        E[Coverage Report<br>Interactive Dashboard]
    end

    A --> B --> C --> D --> E
```

---

## What the AI Returns

| Step | Function | Output |
|------|----------|--------|
| 1 | **SUMMARIZE** | Article counts per country, total coverage volume |
| 2 | **INTERPRET** | Rankings, per-capita metrics, topic breakdown, coverage gaps |
| 3 | **FORMAT** | Bar charts, pie charts, data tables, summary statistics |

---

## Stakeholders & Needs

| Stakeholder | Need |
|-------------|------|
| **Journalist / Editor** | Identify geographic blind spots in publication coverage |
| **Policy Researcher** | Structured country-level media attention data for analysis |

---

## Needs → Goals Mapping

```mermaid
flowchart LR
    subgraph Stakeholders
        S1[Journalist / Editor<br>needs coverage gaps]
        S2[Policy Researcher<br>needs structured data]
    end

    subgraph Goals
        G1[SUMMARIZE<br>article counts]
        G2[INTERPRET<br>rank & patterns]
        G3[FORMAT<br>tables & charts]
    end

    S1 --> G1
    S1 --> G2
    S2 --> G1
    S2 --> G3
```

---

## Tool Summary

| Category | Input → Output | Core Functions |
|----------|----------------|----------------|
| **Global News Attention Tracker** | Guardian API → Country coverage dashboard | SUMMARIZE, INTERPRET, FORMAT |

---

## Files

| File | Description |
|------|-------------|
| `03_guardian_api.py` | Basic Guardian API query (single article) |
| `04_geographic_attention.py` | Multi-country coverage analysis script |
| `../02_productivity/app/app.py` | Interactive Shiny dashboard |
