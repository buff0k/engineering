
import frappe
import requests


@frappe.whitelist()
def ask_ai_agent(question=None):
    user = frappe.session.user

    if not question:
        return {
            "ok": False,
            "message": "Please enter a question."
        }

    api_key = frappe.conf.get("openai_api_key")
    model = frappe.conf.get("openai_model") or "gpt-4.1-mini"

    if not api_key:
        return {
            "ok": False,
            "message": "OpenAI API key is not configured."
        }

    system_prompt = """
You are an AI assistant inside an ERPNext/Frappe system.

Current mode:
- Lab testing only.
- No direct database access.
- No confidential assumptions.
- Answer only from the user's question and provided context.
- If ERP data is needed, say that ERP data tools are not connected yet.

Keep answers practical and short.
"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            },
            timeout=60,
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "message": f"OpenAI error: {response.status_code} - {response.text}"
            }

        data = response.json()

        answer = data.get("output_text")

        if not answer:
            parts = []

            for item in data.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        parts.append(content.get("text", ""))

            answer = "\n".join(parts).strip()

        if not answer:
            answer = "OpenAI returned a response, but no readable text was found." 

        return {
            "ok": True,
            "user": user,
            "question": question,
            "answer": answer
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AI Agent OpenAI Error")

        return {
            "ok": False,
            "message": f"AI Agent error: {str(e)}"
        }