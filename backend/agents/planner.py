"""
Planner Agent — decomposes a user query into structured subtasks.
Calls Groq LLM and returns a deterministic JSON plan.
"""

import json
import os
import re
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are a task planning agent for an AI orchestration system.
Given a user query, decompose it into a JSON array of subtasks.

Each subtask must follow this EXACT schema:
{
  "task_id": <integer starting from 1>,
  "agent": "<retriever|analyzer|writer|validator>",
  "instruction": "<clear, specific instruction for the agent>",
  "depends_on": [<list of task_ids this depends on, empty if independent>]
}

Rules:
- retriever: fetches/searches for information
- analyzer: processes and extracts insights from retrieved data
- writer: generates the final formatted report
- validator: validates the writer output for completeness

Always end with a validator task.
Return ONLY valid JSON array, no markdown fences, no explanation.
"""


def plan_tasks(user_query: str) -> List[Dict]:
    """
    Decompose user query into a list of agent subtasks.
    Returns a list of task dicts.
    Stateless and deterministic.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"User Query: {user_query}"},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

    tasks = json.loads(raw)

    # Normalize: ensure all required fields exist
    for i, task in enumerate(tasks):
        task.setdefault("task_id", i + 1)
        task.setdefault("depends_on", [])
        task["agent"] = task["agent"].strip().lower()

    return tasks


if __name__ == "__main__":
    result = plan_tasks("Research the latest trends in AI and write a comprehensive report.")
    print(json.dumps(result, indent=2))
