from __future__ import annotations

from typing import Protocol

from easyshift_maas.core.contracts import DataSourceProfile, PointCatalog


class CatalogRepositoryProtocol(Protocol):
    def put(self, catalog: PointCatalog) -> PointCatalog: ...

    def get(self, catalog_id: str) -> PointCatalog: ...

    def list_catalog_ids(self) -> list[str]: ...


class DataSourceRegistryProtocol(Protocol):
    def upsert_many(self, profiles: list[DataSourceProfile]) -> None: ...

    def get(self, name: str) -> DataSourceProfile: ...

    def list_profiles(self) -> list[DataSourceProfile]: ...

    def list_by_kind(self, kind: str) -> list[DataSourceProfile]: ...


class InMemoryCatalogRepository:
    def __init__(self) -> None:
        self._storage: dict[str, PointCatalog] = {}

    def put(self, catalog: PointCatalog) -> PointCatalog:
        self._storage[catalog.catalog_id] = catalog
        return catalog

    def get(self, catalog_id: str) -> PointCatalog:
        if catalog_id not in self._storage:
            raise KeyError(f"catalog not found: {catalog_id}")
        return self._storage[catalog_id]

    def list_catalog_ids(self) -> list[str]:
        return sorted(self._storage.keys())


class InMemoryDataSourceRegistry:
    def __init__(self) -> None:
        self._storage: dict[str, DataSourceProfile] = {}

    def upsert_many(self, profiles: list[DataSourceProfile]) -> None:
        for profile in profiles:
            self._storage[profile.name] = profile

    def get(self, name: str) -> DataSourceProfile:
        if name not in self._storage:
            raise KeyError(f"data source profile not found: {name}")
        return self._storage[name]

    def list_profiles(self) -> list[DataSourceProfile]:
        return [self._storage[key] for key in sorted(self._storage.keys())]

    def list_by_kind(self, kind: str) -> list[DataSourceProfile]:
        return [item for item in self.list_profiles() if item.kind.value == kind]
