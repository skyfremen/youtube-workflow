"""Current analytics collector facade with schema-v7 receipt support."""
from analytics import analytics_collection_v6 as impl
from analytics.analytics_collection_v6 import *

SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4, 5, 6, 7}
impl.SUPPORTED_RECEIPT_SCHEMA_VERSIONS = SUPPORTED_RECEIPT_SCHEMA_VERSIONS


def main():
    impl.SUPPORTED_RECEIPT_SCHEMA_VERSIONS = SUPPORTED_RECEIPT_SCHEMA_VERSIONS
    return impl.main()


if __name__ == "__main__":
    main()
