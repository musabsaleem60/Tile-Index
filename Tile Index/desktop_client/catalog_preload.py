"""Warm shared catalogue caches after login."""


def preload_catalogues():
    """Fetch common catalogues once so first screens reuse session cache."""
    from repositories.accessory_repository import AccessoryRepository
    from repositories.branch_repository import BranchRepository
    from repositories.product_repository import ProductRepository

    BranchRepository.get_all()
    ProductRepository.get_all()
    AccessoryRepository.get_all()
