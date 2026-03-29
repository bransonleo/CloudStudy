import json
import logging

from google import genai
from flask import current_app

logger = logging.getLogger(__name__)


def generate(extracted_text, result_type, format_hint=None):
    """Call Gemini to generate content. Returns parsed dict.
    Raises ValueError if response cannot be parsed as JSON."""
    client = genai.Client(api_key=current_app.config["GEMINI_API_KEY"])
    prompt = _build_prompt(extracted_text, result_type, format_hint)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned unparseable JSON for type=%s. Raw: %s",
            result_type, raw[:500],
        )
        raise ValueError("AI response could not be parsed")


def _build_prompt(text, result_type, format_hint):
    material_section = f"\nMaterial:\n{text}"
    if result_type == "summary":
        return (
            "Summarise the following study material into a structured JSON response.\n"
            "Return only valid JSON, no markdown formatting.\n"
            'Return: {"title": "...", "key_points": ["..."], "summary": "..."}'
            + material_section
        )
    elif result_type == "quiz":
        fmt = (
            f"Follow this format instruction: {format_hint}"
            if format_hint
            else "Generate 5 multiple-choice questions, each with 4 options."
        )
        return (
            "Generate quiz questions from the following study material.\n"
            f"{fmt}\n"
            "Return only valid JSON, no markdown formatting.\n"
            'Return JSON: {"questions": [{"question": "...", "options": ["A","B","C","D"],'
            ' "correct_index": 0, "explanation": "..."}]}'
            + material_section
        )
    elif result_type == "flashcards":
        return (
            "Generate flashcards from the following study material.\n"
            "Return only valid JSON, no markdown formatting.\n"
            'Return JSON: {"flashcards": [{"front": "...", "back": "..."}]}'
            + material_section
        )
    else:
        raise ValueError(f"Unknown result_type: {result_type}")
