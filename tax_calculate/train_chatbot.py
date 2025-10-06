# train_chatbot.py
import json
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Paths
BASE = Path(__file__).parent
INTENTS_FILE = BASE / "chatbot_intents.json"
MODEL_FILE = BASE / "chatbot_model.joblib"
META_FILE = BASE / "chatbot_meta.json"

# Load intents JSON
def load_intents(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Prepare training data
def prepare_training(intents):
    X, y, responses = [], [], {}
    for intent in intents["intents"]:
        tag = intent["tag"]
        responses[tag] = intent["responses"]
        for pattern in intent["patterns"]:
            X.append(pattern)
            y.append(tag)
    return X, y, responses

# Train TF-IDF + Naive Bayes and save
def train_and_save():
    intents = load_intents(INTENTS_FILE)
    X, y, responses = prepare_training(intents)

    # Use regex token pattern instead of custom tokenizer
    vectorizer = TfidfVectorizer(token_pattern=r"[a-zA-Z0-9']+", ngram_range=(1, 2))
    clf = MultinomialNB()
    pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", clf)
    ])

    # Train
    pipeline.fit(X, y)

    # Save model
    joblib.dump(pipeline, MODEL_FILE)

    # Save metadata (responses)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"responses": responses}, f, ensure_ascii=False, indent=2)

    print(f"Saved model to {MODEL_FILE} and metadata to {META_FILE}")

# Entry point
if __name__ == "__main__":
    train_and_save()
