"""Central growth-system configuration for Wacky Dramas.

Keep strategy knobs here so planner behavior is auditable and tests can assert the
production policy without scattering magic numbers across the codebase.
"""

DAILY_PUBLISH_COUNT = 24
RAW_CANDIDATE_COUNT = 120
QUALIFIED_TARGET = 60
SEMIFINALIST_TARGET = 36
TITLES_PER_SEMIFINALIST = 5
EXPLORATION_FRACTION = 0.20
CANONICAL_TIMEZONE = "Asia/Singapore"

EDITORIAL_WEIGHTS = {
    "opening_hook_potential": 20,
    "curiosity_gap": 20,
    "emotional_stakes": 15,
    "escalation_potential": 10,
    "payoff_quality": 10,
    "title_potential": 10,
    "broad_relatability": 5,
    "originality": 5,
    "narration_suitability": 5,
}

TITLE_WEIGHTS = {
    "curiosity_gap": 30,
    "emotional_impact": 20,
    "unanswered_question": 15,
    "immediate_comprehension": 10,
    "specificity": 10,
    "natural_phrasing": 5,
    "conciseness": 5,
    "truthful_reflection": 5,
}

HOOK_WEIGHTS = {
    "conflict_speed": 25,
    "unanswered_question": 25,
    "adds_beyond_title": 20,
    "context_efficiency": 15,
    "spoken_naturalness": 10,
    "immediate_comprehension": 5,
}

# The Studio "viewed vs swiped away" value is not exposed by the targeted
# YouTube Analytics API. `engaged_view_rate` (engagedViews / views) is therefore
# used as an explicitly named, API-available continuation proxy and is never
# mislabeled as the Studio metric. Missing metrics are renormalized away.
PERFORMANCE_WEIGHTS = {
    "engaged_view_rate": 25,
    "average_percentage_viewed": 25,
    "average_view_duration_relative": 15,
    "subscribers_per_1000_views": 15,
    "shares_per_1000_views": 10,
    "likes_per_1000_views": 5,
    "comments_per_1000_views": 5,
}

DIVERSITY_LIMITS = {
    "category": 4,
    "conflict": 2,
    "title_style": 3,
}

# These are deliberately compact controlled vocabularies. New values should be
# added intentionally rather than allowing unbounded free-text labels.
CATEGORIES = {
    "RELATIONSHIP", "DATING", "MARRIAGE", "BETRAYAL", "FAMILY", "INHERITANCE",
    "MONEY", "WORKPLACE", "REVENGE", "FRIENDSHIP", "WEDDING", "ENTITLED_PERSON",
    "NEIGHBOR", "SECRETS", "DISCOVERY", "SOCIAL_CONFLICT", "PROPERTY", "PARENTING",
    "MORAL_DILEMMA", "KINDNESS", "MISUNDERSTANDING", "HIDDEN_IDENTITY", "CONSEQUENCES",
    "TWIST", "WILDCARD",
}

EMOTIONS = {
    "ANGER", "BETRAYAL", "INJUSTICE", "EMBARRASSMENT", "FEAR", "DISBELIEF", "REVENGE",
    "LOVE", "GUILT", "REGRET", "SURPRISE", "RELIEF", "HOPE", "SADNESS", "JOY",
}

OPENING_STYLES = {
    "IMMEDIATE_REVELATION", "CONTRADICTION", "DISCOVERY", "CONSEQUENCE_FIRST",
    "URGENT_CONFLICT", "SHOCKING_STATEMENT", "UNANSWERED_EVENT", "DECISION_FIRST",
}

TITLE_STYLES = {
    "HIDDEN_REVELATION", "DISCOVERY", "NORMAL_TO_ABNORMAL", "DECISION_CONSEQUENCE",
    "COUNTDOWN", "UNDERESTIMATED_NARRATOR", "MORAL_CONFLICT", "DELAYED_REVELATION",
    "CONTRADICTION", "CONSEQUENCE_FIRST",
}

ENDING_STYLES = {
    "REVERSAL", "BACKFIRE", "REVEAL", "CONSEQUENCE", "RECONCILIATION", "BOUNDARY_SET",
    "JUSTICE", "SACRIFICE", "KINDNESS_RETURNED", "BITTERSWEET", "OPEN_RESOLUTION",
}

PROTAGONIST_ROLES = {
    "PARTNER", "SPOUSE", "EMPLOYEE", "MANAGER", "SIBLING", "PARENT", "ADULT_CHILD",
    "FRIEND", "ROOMMATE", "NEIGHBOR", "TENANT", "LANDLORD", "CUSTOMER", "OWNER",
    "BRIDE", "GROOM", "STUDENT", "TEACHER", "TRAVELER", "STRANGER", "RELATIVE",
}

ANTAGONIST_ROLES = PROTAGONIST_ROLES | {"COWORKER", "BOSS", "EX_PARTNER", "VENDOR", "GUEST"}

MIN_FINAL_EDITORIAL_SCORE = 68.0
MIN_TITLE_SCORE = 70.0
MIN_HOOK_SCORE = 70.0
NEAR_DUPLICATE_THRESHOLD = 0.82
SOFT_SIMILARITY_THRESHOLD = 0.62

# Confidence curve: analytics influence rises gradually and never removes the
# editorial/exploration contribution. 0 videos => 0%; ~10 => 30%; ~30 => 55%;
# ~60+ approaches the 75% mature cap.
MAX_ANALYTICS_WEIGHT = 0.75
ANALYTICS_CONFIDENCE_SCALE = 22.0

MILESTONE_HOURS = {
    "24h": 24,
    "72h": 72,
    "7d": 168,
}
