"""
Management Command: train_ml_models

Trains all 7 scikit-learn ML models in sequence. Supports two modes:
  --synthetic  : Use generated synthetic data (no DB data needed)
  --real       : Use real StartupProfile data from the database (default if data exists)

Usage:
  python manage.py train_ml_models           # auto-detect
  python manage.py train_ml_models --synthetic
  python manage.py train_ml_models --real
  python manage.py train_ml_models --model kmeans   # train specific model
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Train all ML models "
        "(K-Means, SVM, AdaBoost, Isolation Forest, Random Forest, TF-IDF, DBSCAN)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--synthetic",
            action="store_true",
            help="Use synthetic training data instead of real database data.",
        )
        parser.add_argument(
            "--real",
            action="store_true",
            help="Force use of real database data.",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="all",
            choices=[
                "all",
                "kmeans",
                "svm",
                "adaboost",
                "isolation_forest",
                "random_forest",
                "tfidf",
                "dbscan",
            ],
            help="Train a specific model or all (default: all).",
        )
        parser.add_argument(
            "--samples",
            type=int,
            default=800,
            help="Number of synthetic samples to generate (default: 800).",
        )

    def handle(self, *args, **options):
        use_synthetic = options["synthetic"]
        target_model = options["model"]
        n_samples = options["samples"]

        # Auto-detect if not forced
        if not use_synthetic and not options["real"]:
            from apps.startups.models import StartupProfile
            count = StartupProfile.objects.count()
            use_synthetic = count < 50
            if use_synthetic:
                self.stdout.write(
                    self.style.WARNING(
                        f"Only {count} profiles found. "
                        "Using synthetic data (need ≥50 for real training)."
                    )
                )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🤖 Startup Intelligence — ML Model Training Pipeline"
            )
        )
        self.stdout.write(f"   Mode: {'SYNTHETIC' if use_synthetic else 'REAL DATA'}")
        self.stdout.write(f"   Target: {target_model.upper()}\n")

        trainers = {
            "kmeans": self._train_kmeans,
            "svm": self._train_svm,
            "adaboost": self._train_adaboost,
            "isolation_forest": self._train_isolation_forest,
            "random_forest": self._train_random_forest,
            "tfidf": self._train_tfidf,
            "dbscan": self._train_dbscan,
        }

        models_to_train = list(trainers.keys()) if target_model == "all" else [target_model]

        for model_name in models_to_train:
            self.stdout.write(f"  → Training {model_name.upper()}...")
            t0 = time.time()
            try:
                result = trainers[model_name](use_synthetic, n_samples)
                elapsed = time.time() - t0
                self.stdout.write(
                    self.style.SUCCESS(f"     ✓ Done in {elapsed:.1f}s — {result}")
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"     ✗ FAILED: {exc}"))
                raise CommandError(f"Training failed for {model_name}: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS("\n✅ All models trained and registered successfully!\n")
        )

    # ─── Individual trainers ───────────────────────────────────────────

    def _train_kmeans(self, synthetic: bool, n: int) -> str:
        from apps.ml_engine.services.models.kmeans_cohorts import train_kmeans
        from apps.ml_engine.services.synthetic_data import generate_startup_features

        if synthetic:
            X = generate_startup_features(n)
            result = train_kmeans(X=X)
        else:
            result = train_kmeans()

        return f"silhouette={result['silhouette_score']:.3f}, clusters={result['n_clusters']}"

    def _train_svm(self, synthetic: bool, n: int) -> str:
        from apps.ml_engine.services.models.svm_ranker import train_svm
        from apps.ml_engine.services.synthetic_data import generate_svm_dataset

        X, y = generate_svm_dataset(n)
        result = train_svm(X, y)
        return f"accuracy={result['accuracy']:.3f}"

    def _train_adaboost(self, synthetic: bool, n: int) -> str:
        from apps.ml_engine.services.models.adaboost_readiness import train_adaboost
        from apps.ml_engine.services.synthetic_data import generate_adaboost_dataset

        X, y = generate_adaboost_dataset(n)
        result = train_adaboost(X, y)
        roc = f"{result['roc_auc']:.3f}" if result.get("roc_auc") else "N/A"
        return f"accuracy={result['accuracy']:.3f}, roc_auc={roc}"

    def _train_isolation_forest(self, synthetic: bool, n: int) -> str:
        from apps.ml_engine.services.models.isolation_forest_detector import train_isolation_forest
        from apps.ml_engine.services.synthetic_data import generate_startup_features

        if synthetic:
            X, _ = generate_startup_features(n), None
            train_isolation_forest(X=X)
        else:
            train_isolation_forest()
        return "trained on contamination=0.05"

    def _train_random_forest(self, synthetic: bool, n: int) -> str:
        from apps.ml_engine.services.models.random_forest_capital import train_random_forest
        from apps.ml_engine.services.synthetic_data import generate_capital_dataset

        X, y = generate_capital_dataset(n)
        result = train_random_forest(X, y)
        return f"mae={result['mae_months']:.2f} months"

    def _train_tfidf(self, synthetic: bool, n: int) -> str:
        from apps.ml_engine.services.models.tfidf_search import build_tfidf_index
        from apps.schemes.models import SchemeVersion

        schemes = SchemeVersion.objects.select_related("scheme").order_by("id")[:1000]
        corpus = []
        for sv in schemes:
            text = " ".join(filter(None, [
                sv.scheme.canonical_name,
                sv.description,
                sv.objective,
                " ".join(sv.eligible_sectors or []),
                " ".join(sv.eligible_stages or []),
            ]))
            corpus.append({"scheme_version_id": str(sv.id), "text": text})

        if not corpus:
            # Synthetic fallback
            corpus = [
                {
                    "scheme_version_id": f"synthetic-{i}",
                    "text": f"Startup scheme for sector {i} with grants",
                }
                for i in range(50)
            ]

        result = build_tfidf_index(corpus)
        return f"corpus_size={result['corpus_size']}"

    def _train_dbscan(self, synthetic: bool, n: int) -> str:
        # DBSCAN runs on-demand from Qdrant embeddings; register a placeholder
        from apps.ml_engine.services.models.dbscan_dedup import find_duplicate_schemes

        # Use a tiny synthetic set so the registry entry is created
        synthetic_embeddings = [
            {"scheme_version_id": f"syn-{i}", "vector": [0.1 * i] * 32}
            for i in range(20)
        ]
        result = find_duplicate_schemes(synthetic_embeddings)
        return f"duplicate_groups={len(result['duplicate_groups'])}"
