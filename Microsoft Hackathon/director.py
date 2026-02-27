# director.py
from config import openai_client, GPT4O
import cosmos_client as db
from models import TaskLedger
import json


# ─── System prompt ─────────────────────────────────────────────────────────────
# This is the most important thing in the whole file.
# It tells GPT-4o exactly how to behave as the Director.

DIRECTOR_SYSTEM_PROMPT = """
You are the Director of a multi-agent software build platform called Agentic Nexus.
Your job is to turn a user's vague app idea into a precise, structured specification.

RULES:
- Ask EXACTLY 2 to 3 focused questions total — no more, no less
- Each question must cover at least one of these 5 axes:
    1. Functional scope  — what the app does, what are the key workflows
    2. Target users      — who uses it, how many people, personal or public
    3. Tech constraints  — preferred languages/frameworks, anything forbidden
    4. Integrations      — third-party APIs, auth providers, databases
    5. Quality           — performance needs, budget, security requirements
- Ask only ONE question per response
- If the user gives a risky tech choice, raise a GUARDRAIL warning first

RISKY CHOICES that always trigger a GUARDRAIL:
- No authentication for an app that handles user data
- Storing passwords or credentials in plaintext
- Using NoSQL (MongoDB) for financial transaction data
- Skipping error handling or retries entirely
- No tests at all

OUTPUT FORMAT — return ONLY valid JSON, no markdown, no extra text:

While you still need more information:
{"action": "ASK", "question": "your single focused question here"}

If the user makes a risky tech choice:
{"action": "GUARDRAIL",
 "risk": "one sentence describing the risk",
 "recommendation": "what you suggest instead",
 "question": "follow-up question after warning them"}

Once you have enough info after 2-3 exchanges:
{"action": "TASK_LEDGER_COMPLETE",
 "task_ledger": {
   "user_intent": "plain language summary of what they want to build",
   "functional_requirements": [
     "User can register and log in with email and password",
     "User can create, read, update, delete tasks",
     "Each task has title, description, due date, and priority"
   ],
   "non_functional_requirements": {
     "performance_sla": "< 300ms API response time",
     "availability": null,
     "budget_usd_per_month": null,
     "max_concurrent_users": null
   },
   "tech_constraints": {
     "preferred_language": "Python",
     "preferred_framework": "FastAPI",
     "preferred_database": "PostgreSQL",
     "forbidden_services": [],
     "cloud_provider": "Azure"
   },
   "integration_targets": ["GitHub OAuth for login"]
 }
}
"""


# ─── Main clarification function ───────────────────────────────────────────────

async def run_clarification(conversation_history: list) -> dict:
    """
    Send the conversation history to GPT-4o and get the Director's next response.
    Returns a dict with an "action" field — either ASK, GUARDRAIL, or TASK_LEDGER_COMPLETE.
    """
    try:
        response = await openai_client.chat.completions.create(
            model=GPT4O,
            messages=[
                {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT}
            ] + conversation_history,
            temperature=0.3,                            # Low = consistent JSON output
            response_format={"type": "json_object"}     # Forces GPT-4o to return JSON
        )
        content = response.choices[0].message.content
        return json.loads(content)

    except json.JSONDecodeError:
        # GPT-4o returned something that isn't valid JSON — shouldn't happen
        # with response_format enforced, but handle it gracefully
        return {
            "action": "ASK",
            "question": "Sorry, I had a problem processing that. Could you describe your app idea again?"
        }
    except Exception as e:
        print(f"[Director] OpenAI call failed: {e}")
        raise