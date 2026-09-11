import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from analytics import analytics_collection
from analytics.analytics_learning import build_model, performance_scores, score_candidate
from planning.planning_config import ANALYTICS_MIN_MATURE_VIDEOS


class AnalyticsLearningTests(unittest.TestCase):
    def test_only_canonical_published_receipts_are_eligible(self):
        canonical = {
            "schema_version": 3,
            "publication_mode": "scheduled",
            "publish_at": "2099-09-10T00:00:00Z",
            "planning": {"attributes": {}},
        }
        self.assertTrue(analytics_collection.receipt_eligible(canonical))
        immediate = {
            **canonical,
            "schema_version": 4,
            "publication_mode": "immediate",
            "publish_at": "2099-09-09T15:51:00Z",
        }
        self.assertTrue(analytics_collection.receipt_eligible(immediate))

        for change in (
            {"schema_version": 99},
            {"publication_mode": "public"},
            {"publish_at": None},
            {"planning": None},
        ):
            with self.subTest(change=change):
                receipt = {**canonical, **change}
                self.assertFalse(analytics_collection.receipt_eligible(receipt))

    def test_net_subscriber_rate_uses_gained_minus_lost(self):
        receipt = {
            "schema_version": 3,
            "publication_mode": "scheduled",
            "publish_at": "2099-09-10T00:00:00Z",
            "planning": {"attributes": {}},
            "video_seconds": 130,
            "request_path": "",
        }
        row = {
            "video": "abcdefghijk",
            "views": 1000,
            "engagedViews": 600,
            "averageViewDuration": 90,
            "averageViewPercentage": 70,
            "subscribersGained": 12,
            "subscribersLost": 2,
            "likes": 50,
            "comments": 5,
            "shares": 3,
        }
        enriched = analytics_collection.enrich_row(
            row,
            receipt,
            now_utc=analytics_collection._instant("2099-09-11T01:00:00Z"),
        )
        self.assertEqual(enriched["subscribers_per_1000_views"], 12.0)
        self.assertEqual(enriched["net_subscribers_per_1000_views"], 10.0)
        self.assertTrue(enriched["learning_eligible"])

    def test_performance_is_percentile_normalized_not_raw_units(self):
        entries = [
            {"metrics": {"engaged_view_rate": 20, "average_percentage_viewed": 30}},
            {"metrics": {"engaged_view_rate": 50, "average_percentage_viewed": 60}},
            {"metrics": {"engaged_view_rate": 90, "average_percentage_viewed": 95}},
        ]
        scores = performance_scores(entries)
        self.assertEqual(len(scores), 3)
        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[1], scores[2])
        self.assertGreaterEqual(scores[0], 0)
        self.assertLessEqual(scores[2], 100)

    def test_evidence_count_requires_mature_sample_and_views(self):
        rows = [{"video": f"v{i}", "cohort_eligible": True} for i in range(12)]
        few = {
            "videos": {
                f"v{i}": {"24h": {"metrics": {"views": 1000}}} for i in range(9)
            }
        }
        evidence, mature, views = analytics_collection.evidence_count(rows, few)
        self.assertEqual((evidence, mature), (0, 9))
        self.assertEqual(views, 9000)

        enough_low_views = {
            "videos": {
                f"v{i}": {"24h": {"metrics": {"views": 50}}} for i in range(10)
            }
        }
        evidence, mature, _ = analytics_collection.evidence_count(rows, enough_low_views)
        self.assertEqual(mature, 10)
        self.assertEqual(evidence, 1)

        enough_views = {
            "videos": {
                f"v{i}": {"24h": {"metrics": {"views": 1000}}} for i in range(10)
            }
        }
        evidence, _, _ = analytics_collection.evidence_count(rows, enough_views)
        self.assertEqual(evidence, 10)

    def test_model_uses_age_matched_cohort_and_scores_candidate_attributes(self):
        videos = []
        milestone_videos = {}
        for index in range(ANALYTICS_MIN_MATURE_VIDEOS):
            video_id = f"video-{index}"
            high = index >= ANALYTICS_MIN_MATURE_VIDEOS // 2
            category = "RELATIONSHIP" if high else "WORKPLACE"
            videos.append(
                {
                    "video": video_id,
                    "cohort_eligible": True,
                    "content_dimensions": {
                        "category": category,
                        "conflict": f"C{index}",
                        "primary_emotion": "BETRAYAL",
                        "protagonist_role": "PARTNER",
                        "antagonist_role": "PARTNER",
                        "opening_style": "CONTRADICTION" if high else "DISCOVERY",
                        "title_style": "HIDDEN_REVELATION" if high else "DISCOVERY",
                        "ending_style": "BACKFIRE",
                        "duration_bucket": "135-149",
                    },
                }
            )
            milestone_videos[video_id] = {
                "24h": {
                    "age_hours": 25,
                    "metrics": {
                        "views": 2000 if high else 500,
                        "qualified_shorts_views": 1500 if high else 200,
                        "engaged_view_rate": 80 if high else 40,
                        "average_percentage_viewed": 90 if high else 45,
                        "net_subscribers_per_1000_views": 12 if high else 1,
                        "shares_per_1000_views": 8 if high else 1,
                        "likes_per_1000_views": 60 if high else 10,
                        "comments_per_1000_views": 10 if high else 2,
                    },
                }
            }

        snapshot = {
            "analytics_evidence_count": ANALYTICS_MIN_MATURE_VIDEOS,
            "videos": videos,
        }
        model = build_model(snapshot, {"videos": milestone_videos})
        self.assertEqual(model["model_version"], 1)
        self.assertEqual(model["active_cohort"], "24h")
        self.assertTrue(model["analytics_enabled"])

        components = {
            "curiosity_gap": 90,
            "emotional_impact": 90,
            "unanswered_question": 90,
            "immediate_comprehension": 90,
            "specificity": 90,
            "natural_phrasing": 90,
            "conciseness": 90,
            "truthful_reflection": 90,
        }
        strong = score_candidate(
            {
                "category": "RELATIONSHIP",
                "conflict": "UNSEEN",
                "primary_emotion": "BETRAYAL",
                "protagonist_role": "PARTNER",
                "antagonist_role": "PARTNER",
                "opening_style": "CONTRADICTION",
                "ending_style": "BACKFIRE",
                "target_duration_seconds": 140,
                "title_candidates": [
                    {
                        "title": "Truth #Shorts",
                        "style": "HIDDEN_REVELATION",
                        "truthful": True,
                        "score_components": components,
                    }
                ],
            },
            model,
        )
        weak = score_candidate(
            {
                "category": "WORKPLACE",
                "conflict": "UNSEEN",
                "primary_emotion": "BETRAYAL",
                "protagonist_role": "PARTNER",
                "antagonist_role": "PARTNER",
                "opening_style": "DISCOVERY",
                "ending_style": "BACKFIRE",
                "target_duration_seconds": 140,
                "title_candidates": [
                    {
                        "title": "Truth #Shorts",
                        "style": "DISCOVERY",
                        "truthful": True,
                        "score_components": components,
                    }
                ],
            },
            model,
        )
        self.assertGreater(
            strong["historical_attribute_fit"], weak["historical_attribute_fit"]
        )


if __name__ == "__main__":
    unittest.main()
