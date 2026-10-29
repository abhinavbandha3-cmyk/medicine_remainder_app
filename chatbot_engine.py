"""
AI Medicine Chatbot engine.

Tries Google Gemini API first (if GEMINI_API_KEY is set in the environment).
Falls back to a small offline medicine knowledge base otherwise, so the
chatbot always works out of the box.
"""

import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)

# ---------------------------------------------------------------------------
# Offline knowledge base (used when no Gemini API key is configured, or if
# the Gemini call fails for any reason).
# ---------------------------------------------------------------------------
OFFLINE_KB = {
    "paracetamol": (
        "Paracetamol (Acetaminophen) is a common pain reliever and fever "
        "reducer used for headaches, muscle aches, colds and fever.\n\n"
        "Typical adult dose: 500-1000mg every 4-6 hours, not exceeding "
        "4000mg/day.\nPrecaution: Avoid with heavy alcohol use or liver "
        "disease. Always follow your doctor's prescription."
    ),
    "crocin": (
        "Crocin is a popular brand of Paracetamol used to treat fever, "
        "headache and body pain.\n\nDose: As directed on the pack or by "
        "your doctor, usually every 4-6 hours.\nPrecaution: Do not combine "
        "with other paracetamol-containing products."
    ),
    "vitamin c": (
        "Vitamin C (Ascorbic Acid) is an antioxidant that supports immune "
        "function, skin health and wound healing.\n\nTypical dose: "
        "65-90mg/day for adults, higher doses (500-1000mg) are common in "
        "supplements.\nPrecaution: High doses may cause stomach upset."
    ),
    "ibuprofen": (
        "Ibuprofen is a nonsteroidal anti-inflammatory drug (NSAID) used "
        "for pain, inflammation and fever.\n\nDose: 200-400mg every 4-6 "
        "hours with food.\nPrecaution: Avoid on an empty stomach, and avoid "
        "with peptic ulcers, kidney disease, or during late pregnancy."
    ),
    "aspirin": (
        "Aspirin relieves pain, reduces fever and inflammation, and in low "
        "doses helps prevent blood clots.\n\nDose: Varies widely by "
        "purpose (75mg for heart protection vs 300-600mg for pain) - follow "
        "your doctor's advice.\nPrecaution: Not recommended for children "
        "under 16 due to Reye's syndrome risk."
    ),
    "amoxicillin": (
        "Amoxicillin is a penicillin-type antibiotic used to treat "
        "bacterial infections.\n\nDose: Typically 250-500mg every 8 hours, "
        "as prescribed.\nPrecaution: Complete the full course even if you "
        "feel better; avoid if allergic to penicillin."
    ),
    "cetirizine": (
        "Cetirizine is an antihistamine used to relieve allergy symptoms "
        "such as sneezing, itching and runny nose.\n\nDose: 10mg once "
        "daily for adults.\nPrecaution: May cause mild drowsiness."
    ),
    "metformin": (
        "Metformin is used to control blood sugar levels in type 2 "
        "diabetes.\n\nDose: Commonly 500-1000mg with meals, as prescribed.\n"
        "Precaution: Take with food to reduce stomach upset; report "
        "persistent nausea or muscle pain to your doctor."
    ),
    "omeprazole": (
        "Omeprazole reduces stomach acid and treats acid reflux, ulcers "
        "and heartburn.\n\nDose: Typically 20-40mg once daily before a "
        "meal.\nPrecaution: Long-term use should be monitored by a doctor."
    ),
}

GENERAL_TOPICS = {
    "side effect": (
        "Side effects vary by medicine - common ones include nausea, "
        "drowsiness, or stomach upset. Always read the package leaflet and "
        "tell your doctor about any unusual reaction."
    ),
    "precaution": (
        "General precautions: take medicines exactly as prescribed, avoid "
        "mixing with alcohol unless approved, check for allergies, and "
        "never exceed the recommended dose."
    ),
    "dosage": (
        "Dosage depends on the specific medicine, your age, weight and "
        "condition. Ask me about a specific medicine name for typical "
        "adult dosing, and always confirm with your doctor or pharmacist."
    ),
}


def _offline_answer(message: str) -> str:
    q = message.lower()

    for name, info in OFFLINE_KB.items():
        if name in q:
            return info

    for topic, info in GENERAL_TOPICS.items():
        if topic in q:
            return info

    if any(g in q for g in ("hello", "hi", "hey")):
        return (
            "Hello! I'm your medicine assistant. Ask me about a medicine "
            "(e.g. \"What is Paracetamol?\"), its dosage, or precautions."
        )

    return (
        "I don't have offline information on that yet. I can help with "
        "common medicines like Paracetamol, Crocin, Ibuprofen, Aspirin, "
        "Amoxicillin, Cetirizine, Metformin, Omeprazole and Vitamin C. "
        "For anything else, please consult a doctor or pharmacist."
    )


def _gemini_answer(message: str) -> str | None:
    if not GEMINI_API_KEY:
        return None

    prompt = (
        "You are a concise, careful medicine information assistant inside "
        "a medicine reminder app. Answer the user's question about "
        "medicines, dosage, or precautions in under 120 words. Always "
        "remind the user to consult a doctor for personal medical advice. "
        f"\n\nUser question: {message}"
    )

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def get_chatbot_reply(message: str) -> str:
    if not message or not message.strip():
        return "Please type a question about a medicine."

    reply = _gemini_answer(message)
    if reply:
        return reply

    return _offline_answer(message)
