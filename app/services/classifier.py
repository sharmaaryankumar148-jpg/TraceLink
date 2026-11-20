import logging
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.config import settings

log = logging.getLogger(__name__)


def build_pipeline() -> Pipeline:
    # char n-grams handle hinglish + spelling mistakes better than plain words
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )


class ComplaintClassifier:
    def __init__(self, model_path: Path = settings.model_path):
        self.model_path = model_path
        self._pipeline: Pipeline | None = None

    def _load(self) -> Pipeline:
        if self._pipeline is None:
            if not self.model_path.exists():
                log.warning("No model at %s, training from bundled data", self.model_path)
                from ml.train import train

                train()
            self._pipeline = joblib.load(self.model_path)
        return self._pipeline

    def predict(self, text: str) -> tuple[str, float]:
        pipeline = self._load()
        probabilities = pipeline.predict_proba([text])[0]
        best = probabilities.argmax()
        return str(pipeline.classes_[best]), round(float(probabilities[best]), 3)


classifier = ComplaintClassifier()
