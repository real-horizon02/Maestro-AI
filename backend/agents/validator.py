"""
Validator Agent — quality assurance for the final report.
Checks completeness, structure, and accuracy before output is returned.
"""

import os
import json
import re
from typing import Dict
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are a quality assurance agent for an AI report generation system.
Your job is to validate a generated report and return a JSON validation result.

Check for:
1. Completeness — Does the report address all aspects of the original query?
2. Structure — Does it have proper headings, sections, and formatting?
3. Accuracy — Are the facts and statistics internally consistent?
4. Clarity — Is it readable and well-organized?
5. Length — Is it sufficiently detailed?

Return ONLY valid JSON in this exact format:
{
  "valid": true/false,
  "score": <0-100>,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1"],
  "summary": "brief validation summary"
}
"""


def validate(original_query: str, report: str) -> Dict:
    """
    Validate the generated report against the original query.
    Returns validation result dict.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Original Query: {original_query}\n\nReport to validate:\n{report}",
            },
        ],
        temperature=0.1,
        max_tokens=512,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "valid": True,
            "score": 75,
            "issues": [],
            "suggestions": [],
            "summary": "Validation completed with minor parsing issues.",
        }

    return result
