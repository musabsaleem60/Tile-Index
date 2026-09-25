"""Warm shared catalogue caches after login."""

from concurrent.futures import ThreadPoolExecutor


def preload_catalogues():
    """Fetch common catalogues once so first screens reuse session cache."""
    from repositories.accessory_repository import AccessoryRepository
    from repositories.branch_repository import BranchRepository
    from repositories.product_repository import ProductRepository
    from repositories.sanitary_repository import SanitaryProductRepository
    from desktop_client.config import CATALOG_PRELOAD_TIMEOUT_SECONDS
    from desktop_client.session import api_client

    loaders = (
        BranchRepository.get_all,
        ProductRepository.get_all,
        AccessoryRepository.get_all,
        SanitaryProductRepository.get_all,
    )
    with api_client.timeout_override(CATALOG_PRELOAD_TIMEOUT_SECONDS):
        with ThreadPoolExecutor(max_workers=len(loaders), thread_name_prefix="catalog-preload") as executor:
            futures = [executor.submit(loader) for loader in loaders]
            for future in futures:
                future.result()
