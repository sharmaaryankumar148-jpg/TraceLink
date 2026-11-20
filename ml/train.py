# usage: python -m ml.train [path/to/data.csv]   (csv needs text,category columns)
# saves models/classifier.joblib and models/metrics.json
import csv
import json
import random
import sys
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

from app.config import settings
from app.services.classifier import build_pipeline


def load_csv(path: Path) -> tuple[list[str], list[str], list[str] | None]:
    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("text") and r.get("category")]
    groups = [r["template_id"] for r in rows] if rows and rows[0].get("template_id") else None
    return [r["text"] for r in rows], [r["category"] for r in rows], groups


def _split(texts, labels, groups):
    # for template data, hold out one whole template per category, otherwise the
    # test set is just the train sentences with different numbers (100% accuracy)
    if groups is None:
        return train_test_split(texts, labels, test_size=0.25, random_state=42, stratify=labels)
    rng = random.Random(42)
    by_category: dict[str, set[str]] = {}
    for label, group in zip(labels, groups):
        by_category.setdefault(label, set()).add(group)
    held_out = {rng.choice(sorted(g)) for g in by_category.values()}
    train_idx = [i for i, g in enumerate(groups) if g not in held_out]
    test_idx = [i for i, g in enumerate(groups) if g in held_out]
    pick = lambda items, idx: [items[i] for i in idx]  # noqa: E731
    return pick(texts, train_idx), pick(texts, test_idx), pick(labels, train_idx), pick(labels, test_idx)


def train(data_path: Path | None = None, model_path: Path | None = None) -> dict:
    data_path = Path(data_path or settings.training_data_path)
    model_path = Path(model_path or settings.model_path)

    texts, labels, groups = load_csv(data_path)
    x_train, x_test, y_train, y_test = _split(texts, labels, groups)

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)
    predicted = pipeline.predict(x_test)

    metrics = {
        "dataset": data_path.name,
        "split": "held-out templates" if groups else "stratified 75/25",
        "train_size": len(x_train),
        "test_size": len(x_test),
        "accuracy": round(accuracy_score(y_test, predicted), 4),
        "macro_f1": round(f1_score(y_test, predicted, average="macro"), 4),
        "per_class": classification_report(y_test, predicted, output_dict=True, zero_division=0),
    }

    # final model is trained on everything
    pipeline.fit(texts, labels)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    (model_path.parent / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    result = train(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(f"Trained on {result['dataset']}: accuracy={result['accuracy']}, macro F1={result['macro_f1']} "
          f"(test size {result['test_size']})")
    if "synthetic" in result["dataset"]:
        print("NOTE: synthetic, template-based data. These scores do not reflect real-world accuracy.")
