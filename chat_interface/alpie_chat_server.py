import os
import csv
import json
import re
from flask import Flask, request, Response, jsonify, send_from_directory, stream_with_context
from flask_cors import CORS
from pi169 import Pi169Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

CLIENT = Pi169Client(api_key=os.environ.get("ALPIE_API_KEY"))
MASTER_INDEX_PATH = os.environ.get(
    "MASTER_INDEX_PATH",
    r"P:\AlpineAI_Research_Library\00_Library_Index\master_index.csv",
)
MAX_MESSAGE_LENGTH = 10_000
MAX_HISTORY_ENTRIES = 40
SEARCH_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "what", "when", "where", "which", "who", "why", "with",
}

SYSTEM_PROMPT_BOX1 = """
You are Alpie, a research assistant for the Alpine AI Library.
You answer questions EXCLUSIVELY based on the library content provided to you.
If the retrieved library content does not contain enough information to answer,
say clearly: "I could not find a relevant answer in the Alpine AI Library."
Do NOT use outside knowledge. Do NOT guess or invent information.
Always cite the source title or document name when you use it.
"""

SYSTEM_PROMPT_BOX2 = """
You are Alpie, a deep research analyst for the Alpine AI Library.
Your role is to provide thorough, analytical, and comparative answers
using ONLY the content retrieved from the library.
When answering, connect ideas across multiple sources if relevant.
If nothing relevant is found, say: "The Alpine AI Library does not contain enough
information on this topic for a deep analysis."
Always reference document titles and authors when citing content.
"""

def load_master_index():
    documents = []
    try:
        with open(MASTER_INDEX_PATH, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                documents.append(row)
    except (FileNotFoundError, OSError) as error:
        app.logger.error("Unable to load master index %s: %s", MASTER_INDEX_PATH, error)
    return documents

def search_library(query, documents, top_k=5):
    query_words = set(re.findall(r"[a-z0-9]+", query.lower())) - SEARCH_STOP_WORDS
    if not query_words:
        return []

    scored = []
    for doc in documents:
        document_words = set(
            re.findall(r"[a-z0-9]+", " ".join(str(value) for value in doc.values()).lower())
        )
        score = len(query_words & document_words)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]

def build_context(relevant_docs):
    if not relevant_docs:
        return "No relevant documents found in the library."
    context = ""
    for doc in relevant_docs:
        context += f"\n---\n"
        context += f"Title: {doc.get('Title', 'Unknown')}\n"
        context += f"Authors: {doc.get('Authors', 'Unknown')}\n"
        context += f"Main finding: {doc.get('Main_Finding', 'No main finding available')}\n"
        context += f"Practical application: {doc.get('Practical_Application', 'Not provided')}\n"
    return context

def build_coach_context(summary):
    if not summary:
        return "No rider summary available."

    lines = []
    profile = summary.get("profile") or {}
    lines.append("Rider Summary:")
    lines.append(f"- Risk level: {summary.get('risk_level', 'unknown')}")
    lines.append(f"- Risk score: {summary.get('risk_score', 0)}")
    lines.append(f"- Performance State confidence: {summary.get('confidence', 0.0):.2f}")
    lines.append(f"- Compliance rate: {profile.get('compliance_rate', 'unknown')}")
    lines.append(f"- Rolling ATL/CTL/TSB: {profile.get('rolling_atl', 'unknown')} / {profile.get('rolling_ctl', 'unknown')} / {profile.get('rolling_tsb', 'unknown')}")
    lines.append(f"- Durability index: {profile.get('durability_index', 'unknown')}")
    lines.append(f"- HR decoupling trend: {profile.get('hr_decoupling_trend', 'unknown')}")
    lines.append(f"- RPE delta trend: {profile.get('rpe_delta_trend', 'unknown')}")

    if summary.get("signals"):
        lines.append("Signals:")
        for signal in summary["signals"]:
            lines.append(f"- {signal}")

    if summary.get("rule_citations"):
        lines.append("Rule basis:")
        for citation in summary["rule_citations"]:
            lines.append(f"- {citation.get('rule_id')}: {citation.get('principle')}")

    if summary.get("coach_actions"):
        lines.append("Suggested actions:")
        for action in summary["coach_actions"]:
            lines.append(f"- {action}")

    return "\n".join(lines)

def build_quality_guardrails(summary):
    if not summary:
        return "No rider guardrails available."

    lines = [
        "Quality Guardrails:",
        "- Keep the response rider-specific; avoid generic template language.",
        "- State confidence explicitly when signal quality is limited.",
        "- Include one concrete next action for the coach or rider.",
        "- Do not contradict the current Performance State.",
    ]
    confidence = summary.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.7:
        lines.append("- Treat claims as provisional because Performance State confidence is low.")
    return "\n".join(lines)

def validate_history(history):
    if not isinstance(history, list) or len(history) > MAX_HISTORY_ENTRIES:
        return None

    validated = []
    for entry in history:
        if not isinstance(entry, dict):
            return None
        role = entry.get("role")
        content = entry.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            return None
        validated.append({"role": role, "content": content[:MAX_MESSAGE_LENGTH]})
    return validated

def validate_coach_summary(summary):
    if summary is None:
        return None
    if not isinstance(summary, dict):
        return None

    profile = summary.get("profile")
    if profile is not None and not isinstance(profile, dict):
        return None

    rule_citations = summary.get("rule_citations")
    if rule_citations is not None and not isinstance(rule_citations, list):
        return None

    coach_actions = summary.get("coach_actions")
    if coach_actions is not None and not isinstance(coach_actions, list):
        return None

    if summary.get("quality_constraints") is not None and not isinstance(summary.get("quality_constraints"), list):
        return None

    return summary

@app.route("/")
def index():
    return send_from_directory(app.root_path, "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be JSON."), 400

    user_message = data.get("message")
    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify(error="Message must be a non-empty string."), 400
    user_message = user_message.strip()
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify(error=f"Message must be at most {MAX_MESSAGE_LENGTH} characters."), 400

    history = validate_history(data.get("history", []))
    if history is None:
        return jsonify(error="History has an invalid format or is too long."), 400

    coach_summary = validate_coach_summary(data.get("coach_summary"))
    coach_mode = bool(coach_summary)

    box_id = data.get("box", "box1")
    if box_id not in {"box1", "box2"}:
        return jsonify(error="Unknown chat box."), 400

    system_prompt = SYSTEM_PROMPT_BOX1 if box_id == "box1" and not coach_mode else SYSTEM_PROMPT_BOX2
    if coach_mode:
        system_prompt = """
You are a coach-facing assistant inside the Alpine AI Library.
You must explain rider-specific insight, risk flags, plan rationale, suggested actions,
and research-grounded justifications.
Be transparent when confidence is limited. Do not invent missing rider data.
"""

    documents = load_master_index()
    relevant_docs = search_library(user_message, documents, top_k=10 if box_id == "box2" else 5)
    library_context = build_context(relevant_docs)
    coach_context = build_coach_context(coach_summary) if coach_mode else ""
    quality_guardrails = build_quality_guardrails(coach_summary) if coach_mode else ""

    augmented_message = f"""User Question: {user_message}

Relevant Library Content:
{library_context}

Coach Context:
{coach_context}

Quality Guardrails:
{quality_guardrails}""" if coach_mode else f"""User Question: {user_message}

Relevant Library Content:
{library_context}"""

    messages = [{"role": "system", "content": system_prompt}]
    for entry in history:
        messages.append(entry)
    messages.append({"role": "user", "content": augmented_message})

    def generate():
        try:
            stream = CLIENT.chat.completions.create(
                model="alpie-32b",
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].get("delta", {}).get("content", "")
                if delta:
                    yield f"data: {json.dumps({'text': delta})}\n\n"
        except Exception:
            app.logger.exception("Alpie completion stream failed")
            yield f"data: {json.dumps({'error': 'The model request failed. Please try again.'})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)
