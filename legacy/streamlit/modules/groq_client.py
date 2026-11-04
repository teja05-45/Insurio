"""
Groq API integration module for Insurio.
Handles LLM inference using Groq's ultra-fast inference engine.

API key is loaded exclusively from the .env file:
    GROQ_API_KEY=gsk_...
"""

import os
from typing import Optional
from modules.sanitize import sanitize_llm_response

# Load .env file automatically at import time
try:
    from dotenv import load_dotenv
    load_dotenv()          # reads .env from the project root into os.environ
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False  # python-dotenv not installed; os.environ still works

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


GROQ_MODEL = "llama-3.1-8b-instant"  # Primary model
FALLBACK_MODEL = "mixtral-8x7b-32768"  # Fallback model

SYSTEM_PROMPT = """You are Insurio, an expert insurance policy analyst assistant.
You help users understand their insurance policy documents clearly and accurately.

Your responsibilities:
- Answer questions about coverage, exclusions, waiting periods, and claims
- Cite specific sections from the policy when answering
- Use plain language — avoid jargon unless explaining it
- Be honest when something is not covered or unclear
- Structure answers with clear headings when helpful

OUTPUT FORMAT RULES — follow these strictly:
- Write in plain text or Markdown only (headings with #, bold with **, lists with -)
- Do NOT output any HTML tags such as <div>, <span>, <p>, <br>, <ul>, <li>, <strong>, etc.
- Do NOT output any HTML attributes, inline styles, or CSS
- Do NOT output any JavaScript or code blocks unless the user explicitly asks for code
- Do NOT wrap your response in HTML structure
- If you want to emphasise something, use **bold** or *italic* Markdown, never HTML tags

When answering, always reference the relevant policy context provided.
If the context doesn't contain enough information to answer definitively, say so clearly.
Never fabricate policy details.
"""


def get_api_key() -> str:
    """Read GROQ_API_KEY from environment (populated by .env via python-dotenv)."""
    return os.environ.get("GROQ_API_KEY", "").strip()


def get_groq_client() -> Optional["Groq"]:
    """Initialize and return Groq client using the key from .env."""
    if not GROQ_AVAILABLE:
        return None

    api_key = get_api_key()
    if not api_key:
        return None

    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


def generate_answer(question: str, context: str, chat_history: list = None) -> dict:
    """
    Generate an answer using Groq LLM with policy context.
    
    Args:
        question: User's question
        context: Retrieved policy context from RAG
        chat_history: Previous conversation messages
    
    Returns:
        dict with 'answer' and 'error' keys
    """
    client = get_groq_client()
    
    if not client:
        return {
            "answer": None,
            "error": "⚠️ GROQ_API_KEY not found. Add it to your .env file and restart the app."
        }
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add relevant chat history (last 6 messages for context)
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Build user message with context
    user_message = f"""Policy Context (extracted from uploaded document):
---
{context}
---

User Question: {question}

Please answer the question based on the policy context above. 
Be specific and cite relevant sections where applicable."""
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
        )
        return {
            "answer": sanitize_llm_response(response.choices[0].message.content),
            "error": None
        }
    except Exception as e:
        error_msg = str(e)
        # Try fallback model
        try:
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )
            return {
                "answer": sanitize_llm_response(response.choices[0].message.content),
                "error": None
            }
        except Exception as e2:
            return {
                "answer": None,
                "error": f"API Error: {error_msg}. Please check your API key and try again."
            }


def generate_policy_insights(policy_text: str) -> dict:
    """
    Generate structured policy insights using Groq.
    
    Args:
        policy_text: Full or truncated policy document text
    
    Returns:
        dict with structured insights
    """
    client = get_groq_client()
    
    if not client:
        return {"error": "GROQ_API_KEY not found. Add it to your .env file and restart the app."}
    
    prompt = f"""Analyze this insurance policy document and extract key information.
Return your response as structured text with these exact sections:

## COVERAGE SUMMARY
List the main coverage areas (bullet points)

## WAITING PERIODS
List any waiting periods mentioned (bullet points)

## KEY EXCLUSIONS
List what is NOT covered (bullet points)

## IMPORTANT CLAUSES
List critical policy terms or conditions (bullet points)

## RISK ANALYSIS
Brief 2-3 sentence assessment of coverage gaps or notable risks

Policy Text:
{policy_text[:6000]}
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert insurance policy analyst. Extract and summarize policy information accurately and concisely."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        return {
            "insights": sanitize_llm_response(response.choices[0].message.content),
            "error": None
        }
    except Exception as e:
        return {"insights": None, "error": str(e)}