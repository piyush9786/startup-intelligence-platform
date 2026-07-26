import numpy as np
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ml_engine.models import MLModelRegistry
from apps.ml_engine.services.feature_pipeline import FEATURE_DIM, extract_features
from apps.ml_engine.services.models.adaboost_readiness import train_adaboost
from apps.ml_engine.services.models.isolation_forest_detector import train_isolation_forest
from apps.ml_engine.services.models.kmeans_cohorts import train_kmeans
from apps.ml_engine.services.models.random_forest_capital import train_random_forest
from apps.ml_engine.services.models.svm_ranker import train_svm
from apps.ml_engine.services.models.tfidf_search import build_tfidf_index, sparse_search
from apps.ml_engine.services.synthetic_data import (
    generate_adaboost_dataset,
    generate_capital_dataset,
    generate_startup_features,
    generate_svm_dataset,
)
from apps.startups.models import StartupProfile

User = get_user_model()


class MLEngineTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ml_user", password="password")
        self.profile = StartupProfile.objects.create(
            owner=self.user,
            startup_name="AI Startup Inc",
            stage="mvp",
            sectors=["fintech", "ai & software"],
            annual_turnover=500000,
            team_size=10,
        )

    def test_feature_extraction(self):
        vec = extract_features(self.profile)
        self.assertEqual(vec.shape, (FEATURE_DIM,))
        self.assertIsInstance(vec, np.ndarray)

    def test_kmeans_training(self):
        X = generate_startup_features(50)
        res = train_kmeans(X=X)
        self.assertIn("silhouette_score", res)
        self.assertTrue(MLModelRegistry.objects.filter(model_type="kmeans").exists())

    def test_svm_training(self):
        X, y = generate_svm_dataset(50)
        res = train_svm(X, y)
        self.assertIn("accuracy", res)
        self.assertTrue(MLModelRegistry.objects.filter(model_type="svm").exists())

    def test_adaboost_training(self):
        X, y = generate_adaboost_dataset(50)
        res = train_adaboost(X, y)
        self.assertIn("accuracy", res)
        self.assertTrue(MLModelRegistry.objects.filter(model_type="adaboost").exists())

    def test_isolation_forest_training(self):
        X = generate_startup_features(50)
        res = train_isolation_forest(X=X)
        self.assertIsNotNone(res)
        self.assertTrue(MLModelRegistry.objects.filter(model_type="isolation_forest").exists())

    def test_random_forest_training(self):
        X, y = generate_capital_dataset(50)
        res = train_random_forest(X, y)
        self.assertIn("mae_months", res)
        self.assertTrue(MLModelRegistry.objects.filter(model_type="random_forest").exists())

    def test_tfidf_search(self):
        corpus = [
            {"scheme_version_id": "sv-1", "text": "Fintech startup grant for early stage AI"},
            {"scheme_version_id": "sv-2", "text": "Agritech loan for farm machinery"},
        ]
        result = build_tfidf_index(corpus)
        model_reg = result["registry"]
        model_reg.deployment_stage = "production"
        model_reg.production_approved = True
        model_reg.save()
        results = sparse_search("fintech grant", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["scheme_version_id"], "sv-1")
