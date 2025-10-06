import json
import re
import joblib
from pathlib import Path
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE = Path(__file__).parent
MODEL_FILE = BASE / "chatbot_model.joblib"
META_FILE = BASE / "chatbot_meta.json"

_model = None
_meta = None

import re


def simple_tokenize(text):
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z0-9']+", text)
    return tokens



def normalize_text(text: str):
    """Lowercase and strip"""
    return text.lower().strip()

def correct_spelling(text: str):
    """Dummy spelling correction (for now just return text)"""
    return text

def censor(text: str):
    """Dummy censor function, returns text unchanged"""
    return text

# Load model & meta
def load_model():
    global _model, _meta
    if _model is None:
        _model = joblib.load(MODEL_FILE)
    if _meta is None:
        with open(META_FILE, 'r', encoding='utf-8') as f:
            _meta = json.load(f)
    return _model, _meta

# Normalize text
def normalize_text(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Predict with TF-IDF similarity + random response
def predict_response(user_text, session_id=None):
    model, meta = load_model()
    normalized = normalize_text(user_text)

    # Get intent probabilities
    probs = model.predict_proba([normalized])[0]
    classes = model.classes_
    best_idx = probs.argmax()
    best_tag = classes[best_idx]
    confidence = float(probs[best_idx])

    CONFIDENCE_THRESHOLD = 0.35
    if confidence < CONFIDENCE_THRESHOLD:
        # fallback: try cosine similarity with training patterns
        intents_file = BASE / "chatbot_intents.json"
        with open(intents_file, 'r', encoding='utf-8') as f:
            intents_data = json.load(f)

        patterns = []
        tags = []
        for intent in intents_data['intents']:
            for p in intent['patterns']:
                patterns.append(p)
                tags.append(intent['tag'])

        vectorizer = model.named_steps['tfidf']
        user_vec = vectorizer.transform([normalized])
        pattern_vecs = vectorizer.transform(patterns)
        sims = cosine_similarity(user_vec, pattern_vecs)[0]

        max_idx = sims.argmax()
        if sims[max_idx] > 0.3:
            best_tag = tags[max_idx]
            confidence = float(sims[max_idx])
        else:
            best_tag = "fallback"
            confidence = 0.0

    responses = meta.get("responses", {}).get(best_tag, ["Sorry, I didn't understand."])
    response = random.choice(responses)

    return {
        "intent": best_tag,
        "response": response,
        "confidence": round(confidence, 3),
        "normalized": normalized
    }
