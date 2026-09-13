"""Current analytics collector entrypoint with schema-v7 receipt support.

The proven collector implementation remains in analytics_collection_v6. Imported
callers receive that exact module object so private helpers, monkeypatch points and
global state retain their historical semantics; only supported receipt versions
advance for schema-v7 success receipts.
"""
import sys

from analytics import analytics_collection_v6 as impl

SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4, 5, 6, 7}
impl.SUPPORTED_RECEIPT_SCHEMA_VERSIONS = SUPPORTED_RECEIPT_SCHEMA_VERSIONS

if __name__ == "__main__":
    impl.main()
else:
    sys.modules[__name__] = impl
