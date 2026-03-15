# Pokemon Tournament 3-Agent Workflow (Mermaid)

This document describes the synthetic-data 3-agent workflow using Mermaid diagrams. The pipeline generates 4 fictional Pokemon, runs a single-elimination tournament over every possible bracket seeding, and produces a judge/commentator-style report.

---

## 1. High-level flow

Information moves in one direction: User prompt → Agent 1 → Agent 2 → Agent 3 → Final report.

```mermaid
flowchart LR
  Prompt[User prompt]
  Gen[Agent 1 Generator]
  Analyst[Agent 2 Tournament Analyst]
  Judge[Agent 3 Judge Commentator]
  Report[Formatted report]

  Prompt -->|"Request: 4 Pokemon table"| Gen
  Gen -->|"4 Pokemon and stats"| Analyst
  Analyst -->|"Win rates and bracket analysis"| Judge
  Judge -->|"Judge commentary report"| Report
```

---

## 2. What each agent does

Each agent has a clear input and output; the table below is summarized in the diagram.

| Agent | Input | Output |
|-------|--------|--------|
| 1 Generator | User prompt (request 4 Pokemon) | Markdown table: name, type, HP, attack, defense |
| 2 Tournament Analyst | 4-Pokemon stats table | Win counts, when each won or lost, matchup notes |
| 3 Judge Commentator | Win rates and bracket analysis | Formatted report with verdict and commentator facts |

```mermaid
flowchart LR
  subgraph GenBox [Agent 1: Generator]
    G[Creates exactly 4 fictional Pokemon]
  end

  subgraph AnalystBox [Agent 2: Tournament Analyst]
    A[Runs 24 bracket orderings and records winners]
  end

  subgraph JudgeBox [Agent 3: Judge Commentator]
    J[Writes judge and commentator report]
  end

  Prompt2[User prompt] -->|"task"| GenBox
  GenBox -->|"4-Pokemon table"| AnalystBox
  AnalystBox -->|"Win rates and analysis"| JudgeBox
  JudgeBox --> Report2[Formatted report]
```

---

## 3. Why exactly 4 Pokemon?

The second agent tries **every possible route** (every way to seed the 4 Pokemon into the bracket). That means 4! = 24 orderings. More Pokemon would make this step very expensive.

```mermaid
flowchart LR
  Four[4 Pokemon] --> Perm[4 factorial orderings]
  Perm --> TwentyFour["24 bracket seedings"]
  TwentyFour --> Run[Agent 2 runs 24 tournaments]
  Run --> Stats[Win count per Pokemon across all 24]
```

---

## 4. Tournament step in detail

Agent 2 takes the 4 Pokemon and, for each of the 24 orderings, fills a single-elimination bracket, simulates matchups using stats and type logic, and records the winner.

```mermaid
flowchart TB
  Table[4-Pokemon stats table]
  Table --> Seed[For each of 24 seedings]
  Seed --> Bracket[Fill bracket: Semi1 Semi2 then Final]
  Bracket --> Sim[Simulate each matchup with stats and types]
  Sim --> Winner[Record tournament winner]
  Winner --> Aggregate[Aggregate: win count per Pokemon]
  Aggregate --> Notes[Add when each lost and matchup insights]
  Notes --> ToAgent3[Structured analysis to Agent 3]
```

---

## 5. End-to-end data flow (simplified)

A minimal view of what moves between agents.

```mermaid
flowchart LR
  P[Prompt]
  T1[Table 4 rows]
  T2[Analysis text]
  T3[Report text]

  P -->|"task"| T1
  T1 -->|"task"| T2
  T2 -->|"task"| T3
```

In code: Agent 1 output becomes the `task` for Agent 2; Agent 2 output becomes the `task` for Agent 3 (e.g. using `agent_run(role=..., task=..., model=...)` in `functions.py`).
