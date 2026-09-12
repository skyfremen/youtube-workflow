import copy
import unittest

from planning import ranked_promotion
from test_request_schema import valid_request
from validation.validate_content import validate_request_data


def v5_request():
    data = valid_request()
    data["schema_version"] = 5
    data["visual"]["background_primary_treatment"] = {
        "segment_start_seconds": 0.0,
        "segment_duration_seconds": 12.0,
        "playback_rate": 1.25,
    }
    data["visual"]["background_backup_treatment"] = {
        "segment_start_seconds": 0.0,
        "segment_duration_seconds": 12.0,
        "playback_rate": 1.25,
    }
    return data


def ranked_items(count):
    items = []
    for rank in range(1, count + 1):
        request = v5_request()
        request["content_id"] = f"wd-20990910T000000-ranked-{rank:02d}-a1b2c3"
        items.append({
            "rank": rank,
            "candidate_id": f"candidate-{rank:02d}",
            "request": request,
        })
    return items


class RankedPoolContractTests(unittest.TestCase):
    def test_daily_and_adhoc_pool_sizes_are_fixed(self):
        self.assertEqual(ranked_promotion.DAILY_POOL_SIZE, 36)
        self.assertEqual(ranked_promotion.ADHOC_POOL_SIZE, 5)
        self.assertEqual(ranked_promotion.NORMAL_DAILY_TARGET, 24)

    def test_ranked_candidate_validator_preserves_declared_order(self):
        items = ranked_items(36)
        candidates, ids = ranked_promotion._validate_ranked_candidates(items and {"ranked_candidates": items}, 36)
        self.assertEqual(candidates, items)
        self.assertEqual(ids, [f"candidate-{rank:02d}" for rank in range(1, 37)])

    def test_ranked_candidate_validator_rejects_wrong_size_or_rank_gap(self):
        with self.assertRaises(ranked_promotion.PromotionError):
            ranked_promotion._validate_ranked_candidates(
                {"ranked_candidates": ranked_items(35)}, 36
            )
        broken = ranked_items(5)
        broken[2]["rank"] = 4
        with self.assertRaises(ranked_promotion.PromotionError):
            ranked_promotion._validate_ranked_candidates(
                {"ranked_candidates": broken}, 5
            )

    def test_v5_hard_registry_validation_accepts_current_safe_defaults(self):
        errors = validate_request_data(v5_request(), enforce_registry=True)
        self.assertEqual(errors, [])

    def test_v5_hard_registry_validation_rejects_unknown_asset(self):
        data = v5_request()
        data["visual"]["background_primary_id"] = "missing-background"
        errors = validate_request_data(data, enforce_registry=True)
        self.assertTrue(any("unknown background asset" in error for error in errors))

    def test_v5_hard_registry_validation_rejects_treatment_past_asset_end(self):
        data = v5_request()
        data["visual"]["background_primary_treatment"] = {
            "segment_start_seconds": 15.0,
            "segment_duration_seconds": 12.0,
            "playback_rate": 1.25,
        }
        errors = validate_request_data(data, enforce_registry=True)
        self.assertTrue(any("exceeds background" in error for error in errors))

    def test_validation_never_mutates_ai_authored_request(self):
        data = v5_request()
        original = copy.deepcopy(data)
        validate_request_data(data, enforce_registry=True)
        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main()
