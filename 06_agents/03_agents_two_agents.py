"""03_agents_two_agents.py
Simple 2-Agent Workflow Example
Pairs with 03_agents.py
Tim Fraser

This script demonstrates a simple two-agent workflow.
Agent 1 summarizes raw data, and Agent 2 formats that summary
for a human-friendly report. Students will learn how to pass
information between agents in a small, clear example.
"""

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os
from pathlib import Path

import pandas as pd  # for data manipulation

# If you haven't already, install this package...
# pip install pandas


## 0.2 Set Working Directory #################################

# Set working directory to this script's folder.
# This makes relative imports and file paths consistent.
this_file = Path(__file__).resolve()
os.chdir(this_file.parent)


## 0.3 Load Agent Helper Functions #################################

# We reuse the same helper functions as in 03_agents.py.
from functions import agent_run, df_as_text  # noqa: E402


# 1. LOAD OR CREATE DATA ###################################

## 1.1 Create a Simple Example Dataset #################################

# For this example, we will create a small in-memory dataset.
# In a real workflow, you might load this from a CSV or API.
data = pd.DataFrame(
    {
        "product": ["Aspirin", "Ibuprofen", "Acetaminophen", "Aspirin", "Ibuprofen"],
        "region": ["North", "South", "East", "West", "North"],
        "units_sold": [120, 80, 150, 200, 90],
    }
)


## 1.2 Convert Data to Text for the Agent #################################

# Convert the data to a text string so the agent can read it.
raw_data_text = df_as_text(data)


# 2. DEFINE AGENTS ###################################

MODEL = "smollm2:135m"


## 2.1 Agent 1 - Data Summary Agent #################################

role_summary = (
    "I am a data analyst. "
    "The user will give me a small table of data as plain text. "
    "I will summarize the overall patterns in the data in 3-5 bullet points, "
    "including key totals or averages, without doing any formatting beyond bullets."
)


## 2.2 Agent 2 - Formatter Agent #################################

role_formatter = (
    "I am a report writer. "
    "The user will give me a short bullet-point summary of some data. "
    "I will turn this into a short, well-structured markdown report with a title, "
    "subheadings, and a brief narrative explanation suitable for a manager."
)


# 3. RUN WORKFLOW ###################################

## 3.1 Agent 1: Summarize the Raw Data #################################

print("=== Agent 1: Data Summary ===")
summary_text = agent_run(
    role=role_summary,
    task=raw_data_text,
    model=MODEL,
    output="text",
)
print(summary_text)
print("\n")  # blank line between stages


## 3.2 Agent 2: Format the Summary #################################

print("=== Agent 2: Formatted Report ===")
formatted_report = agent_run(
    role=role_formatter,
    task=summary_text,
    model=MODEL,
    output="text",
)
print(formatted_report)


# 4. NOTES ###################################

# In this two-agent chain:
# - Agent 1 takes the raw table (as text) and produces a concise summary.
# - Agent 2 takes that summary and converts it into a formatted markdown report.
# This mirrors the idea of separating "analysis" from "communication",
# while keeping the workflow simpler than the three-agent example.

