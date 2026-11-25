import os
import json
import tarfile
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report

def train_model():
    df = pd.read_csv("data/telcoaustral_tickets.csv")
    X = df["text"]
    y = df["intent"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    hyperparams = {
        "vectorizer": "TfidfVectorizer(ngram_range=(1, 2), max_features=3000)",
        "classifier": "LogisticRegression(C=2.0, max_iter=500, random_state=42)",
        "confidence_threshold": 0.75
    }

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=3000)),
        ("clf", LogisticRegression(C=2.0, max_iter=500, random_state=42))
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted")

    metrics = {
        "accuracy": round(float(acc), 4),
        "precision_weighted": round(float(prec), 4),
        "recall_weighted": round(float(rec), 4),
        "f1_score_weighted": round(float(f1), 4),
        "test_samples": len(y_test),
        "hyperparameters": hyperparams
    }

    print("=== MÉTRICAS DEL MODELO (IE10 - Ítem 2.3.d) ===")
    print(json.dumps(metrics, indent=2))
    print("\nReporte por intención:")
    print(classification_report(y_test, y_pred))

    os.makedirs("model_artifacts", exist_ok=True)
    joblib.dump(pipeline, "model_artifacts/model.joblib")
    with open("model_artifacts/metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    with tarfile.open("model_artifacts/model.tar.gz", "w:gz") as tar:
        tar.add("model_artifacts/model.joblib", arcname="model.joblib")
        tar.add("sagemaker/inference.py", arcname="code/inference.py")

    print("\nArtefacto listo para AWS SageMaker: model_artifacts/model.tar.gz")

if __name__ == "__main__":
    train_model()