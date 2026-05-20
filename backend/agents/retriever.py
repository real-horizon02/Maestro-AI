"""
Retriever Agent — searches and retrieves relevant information.
Uses Groq to simulate intelligent retrieval from its training knowledge.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are an expert information retrieval agent.
Your job is to retrieve comprehensive, factual information based on the given instruction.
Return detailed, structured information as if you retrieved it from authoritative sources.
Include statistics, facts, examples, and relevant context.
Format your response as rich informational content, not as a conversation.
"""


def retrieve(instruction: str) -> str:
    """
    Retrieve relevant information based on the instruction.
    Returns raw retrieved text.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()
