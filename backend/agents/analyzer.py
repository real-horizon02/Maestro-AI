"""
Analyzer Agent — processes and extracts insights from retrieved data.
Summarizes, identifies trends, and produces structured analysis.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are an expert data analysis agent.
Given retrieved information, your job is to:
1. Identify key trends and patterns
2. Extract the most important insights
3. Summarize complex data clearly
4. Highlight notable statistics or findings
5. Structure your analysis with clear sections

Be analytical, precise, and thorough. Format with clear headings and bullet points.
"""


def analyze(instruction: str, context: str = "") -> str:
    """
    Analyze data based on instruction and optional context from retriever.
    Returns structured analysis text.
    """
    user_content = instruction
    if context:
        user_content = f"{instruction}\n\nRetrieved Context:\n{context}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()
