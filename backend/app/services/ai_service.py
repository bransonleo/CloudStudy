import json
import logging

from google import genai
from flask import current_app, request

logger = logging.getLogger(__name__)


def generate(extracted_text, result_type, format_hint=None):
    """Call Gemini to generate content. Returns parsed dict.
    Raises ValueError if response cannot be parsed as JSON."""
    # Use user-provided API key from request header, fall back to server config
    api_key = request.headers.get("X-Gemini-Api-Key") or current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("No Gemini API key provided. Please set your API key in Settings.")
    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(extracted_text, result_type, format_hint)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # remove ```json line
        raw = raw.rsplit("```", 1)[0]  # remove closing ```
        raw = raw.strip()
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
            "Generate as many flashcards as possible from the following study material. "
            "Cover every key concept, term, and detail.\n"
            "Return only valid JSON, no markdown formatting.\n"
            'Return JSON: {"flashcards": [{"front": "...", "back": "..."}]}'
            + material_section
        )
    else:
        raise ValueError(f"Unknown result_type: {result_type}")
