# lab_pokemon_tournament.py
# Pokemon Tournament 3-Agent Workflow (Lab)
# Pairs with lab_pokemon_tournament_workflow.md
# Tim Fraser

# This script implements the 3-agent workflow: generate 4 fictional Pokemon,
# run a single-elimination tournament over all 24 bracket orderings, and
# produce a judge/commentator-style report. It uses rules from pokemon_rules.yaml
# and helper functions from functions.py.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os
from pathlib import Path

import yaml

# pip install pyyaml

## 0.2 Set Working Directory #################################

this_file = Path(__file__).resolve()
os.chdir(this_file.parent)

## 0.3 Load Functions and Rules #################################

from functions import agent_run

# Load rules for consistent agent behavior (same pattern as 04_rules.py)
with open("pokemon_rules.yaml", "r") as f:
    rules_config = yaml.safe_load(f)

rules_gen = rules_config["rules"]["pokemon_generator"][0]
rules_analyst = rules_config["rules"]["tournament_analyst"][0]
rules_judge = rules_config["rules"]["judge_commentator"][0]


def format_rules_for_prompt(ruleset):
    """Format a ruleset into a string to include in the agent's system prompt."""
    return f"{ruleset['name']}\n{ruleset['description']}\n\n{ruleset['guidance']}"


# 1. CONFIGURATION ###################################

MODEL = "smollm2:1.7b"

# User prompt for Agent 1: request exactly 4 fictional Pokemon in table form
TASK_AGENT1 = (
    "Generate exactly 4 fictional Pokemon. "
    "Output a single markdown table with columns: name, type, HP, attack, defense. "
    "Use invented names and types only (no real Pokemon). "
    "Use positive integers for HP, attack, and defense (e.g. between 50 and 120)."
)


# 2. SYSTEM PROMPTS (Role, Format, Constraints) #################################

# Agent 1: Pokemon Generator
# Role: synthetic data generator. Format: one markdown table, 4 rows, 5 columns. Constraint: invented only.
# Refinement: explicitly require "reply with only the table" to avoid preamble or commentary.
ROLE_AGENT1_BASE = (
    "You are a synthetic data generator. Your only job is to produce a table of exactly 4 fictional Pokemon "
    "with stats for a tournament (name, type, HP, attack, defense). "
    "Reply with ONLY the markdown table: no sentence before or after, no explanation. Exactly 4 rows."
)
ROLE_AGENT1 = f"{ROLE_AGENT1_BASE}\n\n{format_rules_for_prompt(rules_gen)}"

# Agent 2: Tournament Analyst
# Role: run single-elimination over all 24 bracket orderings; output win counts and when each lost.
# Refinement: require explicit section headings so Agent 3 can parse reliably.
ROLE_AGENT2_BASE = (
    "You are a tournament analyst. You receive a table of 4 Pokemon (name, type, HP, attack, defense). "
    "Run a single-elimination tournament for every possible seeding of these 4 into the bracket (24 orderings). "
    "For each matchup use the given stats and type advantages to decide the winner. "
    "Your reply must use these exact section headings: 'Win count', 'When they didn't win', 'Matchup notes'. "
    "Under Win count list each Pokemon and how many of the 24 tournaments they won. Under When they didn't win briefly note in what seedings or matchups each lost."
)
ROLE_AGENT2 = f"{ROLE_AGENT2_BASE}\n\n{format_rules_for_prompt(rules_analyst)}"

# Agent 3: Judge / Commentator
# Role: turn analysis into a formatted judge and commentator report.
# Refinement: require markdown structure (title, Win rates, When they didn't win, Commentator highlights, Verdict).
ROLE_AGENT3_BASE = (
    "You are a judge and commentator. You receive tournament analysis (win counts, when each Pokemon lost, matchup notes). "
    "Produce a polished report. Use markdown: a main title, then sections 'Win rates', 'When they didn't win', 'Commentator highlights', and 'Verdict'. "
    "Cite only the numbers and facts from the analysis; do not invent data. Use an authoritative but engaging commentator voice."
)
ROLE_AGENT3 = f"{ROLE_AGENT3_BASE}\n\n{format_rules_for_prompt(rules_judge)}"


# 3. WORKFLOW EXECUTION ###################################

print("=== Agent 1: Pokemon Generator ===\n")
result1 = agent_run(role=ROLE_AGENT1, task=TASK_AGENT1, model=MODEL, output="text")
print(result1)
print("\n" + "=" * 60 + "\n")

print("=== Agent 2: Tournament Analyst ===\n")
result2 = agent_run(role=ROLE_AGENT2, task=result1, model=MODEL, output="text")
print(result2)
print("\n" + "=" * 60 + "\n")

print("=== Agent 3: Judge / Commentator ===\n")
result3 = agent_run(role=ROLE_AGENT3, task=result2, model=MODEL, output="text")
print(result3)


# 4. OBSERVATIONS AND REFINEMENT NOTES #################################

# After running, verify:
# - Agent 1: Output is exactly one markdown table with 4 rows and columns name, type, HP, attack, defense.
#   If you see extra text before/after the table, the prompt already says "Reply with ONLY the table"; you can add "Do not include any other text." to the user task.
# - Agent 2: Reply includes "Win count" (each Pokemon and wins out of 24), "When they didn't win", and "Matchup notes".
#   If win counts are missing or vague, add to the prompt: "Include a line per Pokemon: [Name] won X of 24 tournaments."
# - Agent 3: Report has clear sections (Win rates, When they didn't win, Commentator highlights, Verdict) and does not invent numbers.
#   If the report is too short or skips sections, repeat the required section names in the user message or in the role.
#
# Refinements already applied in this script:
# a) Agent 1: "Reply with ONLY the markdown table" and "Exactly 4 rows" to reduce preamble and enforce count.
# b) Agent 2: Required section headings "Win count", "When they didn't win", "Matchup notes" for consistent structure.
# c) Agent 3: Required markdown sections (Win rates, When they didn't win, Commentator highlights, Verdict) and "do not invent data".
