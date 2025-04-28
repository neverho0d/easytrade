# src/marketplace_aggregator/services/exceptions.py


class ServiceError(Exception):
    """Base class for service layer exceptions."""

    pass


class RuleNotFoundError(ServiceError):
    """Raised when a specific PromotionalRule ID is not found."""

    def __init__(self, rule_id: int):
        self.rule_id = rule_id
        super().__init__(f"PromotionalRule with ID '{rule_id}' not found.")


class RuleInactiveError(ServiceError):
    """Raised when a PromotionalRule is found but is not active."""

    def __init__(self, rule_id: int):
        self.rule_id = rule_id
        super().__init__(f"PromotionalRule '{rule_id}' is not active.")


class ProductNotFoundError(ServiceError):
    """Raised when a product identifier (SKU/group_id) is not found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Product/Group with identifier '{identifier}' not found.")


class ListingPreparationError(ServiceError):
    """Raised during issues while preparing data before calling the adapter."""

    pass


class AdapterNotFoundError(ServiceError):
    """Raised when a required marketplace adapter is not configured."""

    def __init__(self, marketplace_name: str):
        self.marketplace_name = marketplace_name
        super().__init__(f"Marketplace adapter '{marketplace_name}' not configured.")


class ListingRecordGetError(ServiceError):
    """Raised when getting the internal Listing record fails."""

    def __init__(self, listing_id: str):
        self.listing_id = listing_id
        super().__init__(f"Failed to get internal record for listing ID {listing_id}")


class ListingRecordSaveError(ServiceError):
    """Raised when saving the internal Listing record fails after successful submission."""

    def __init__(self, listing_id: str, original_exception: Exception):
        self.listing_id = listing_id
        self.original_exception = original_exception
        super().__init__(
            f"Failed to save internal record for listing ID {listing_id}: {original_exception}"
        )
