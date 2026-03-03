"""
TCO Comparison Model — ERP Connector Abstraction
Factory pattern for SAP, Oracle, Infor, and generic ERP/EAM integrations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

from utils.logging_config import get_logger

log = get_logger("erp_connector")


@dataclass
class ERPConnectionConfig:
    """ERP connection configuration."""
    system_type: str  # "sap", "oracle", "infor", "generic"
    host: str = ""
    port: int = 0
    username: str = ""
    api_key: str = ""
    base_url: str = ""
    extra: dict = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class ERPConnector(ABC):
    """Abstract base class for ERP system connectors."""

    def __init__(self, config: ERPConnectionConfig):
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to ERP system."""
        ...

    @abstractmethod
    def extract_equipment_master(self) -> pd.DataFrame:
        """Extract equipment master data."""
        ...

    @abstractmethod
    def extract_maintenance_history(self) -> pd.DataFrame:
        """Extract maintenance/work order history."""
        ...

    @abstractmethod
    def extract_spare_parts_catalog(self) -> pd.DataFrame:
        """Extract spare parts and pricing."""
        ...

    @abstractmethod
    def extract_purchase_orders(self) -> pd.DataFrame:
        """Extract procurement/purchase order data."""
        ...

    def health_check(self) -> bool:
        return self._connected


class SAPConnector(ERPConnector):
    """SAP S/4HANA & ECC connector (placeholder — requires SAP RFC/OData)."""

    def connect(self) -> bool:
        log.info("SAP connector: connection placeholder (requires pyrfc or OData config)")
        self._connected = False
        return False

    def extract_equipment_master(self) -> pd.DataFrame:
        log.warning("SAP extract_equipment_master: not yet implemented")
        return pd.DataFrame()

    def extract_maintenance_history(self) -> pd.DataFrame:
        log.warning("SAP extract_maintenance_history: not yet implemented")
        return pd.DataFrame()

    def extract_spare_parts_catalog(self) -> pd.DataFrame:
        log.warning("SAP extract_spare_parts_catalog: not yet implemented")
        return pd.DataFrame()

    def extract_purchase_orders(self) -> pd.DataFrame:
        log.warning("SAP extract_purchase_orders: not yet implemented")
        return pd.DataFrame()


class OracleConnector(ERPConnector):
    """Oracle EAM / Fusion connector (placeholder)."""

    def connect(self) -> bool:
        log.info("Oracle connector: connection placeholder")
        self._connected = False
        return False

    def extract_equipment_master(self) -> pd.DataFrame:
        return pd.DataFrame()

    def extract_maintenance_history(self) -> pd.DataFrame:
        return pd.DataFrame()

    def extract_spare_parts_catalog(self) -> pd.DataFrame:
        return pd.DataFrame()

    def extract_purchase_orders(self) -> pd.DataFrame:
        return pd.DataFrame()


class InforConnector(ERPConnector):
    """Infor EAM connector (placeholder)."""

    def connect(self) -> bool:
        log.info("Infor connector: connection placeholder")
        self._connected = False
        return False

    def extract_equipment_master(self) -> pd.DataFrame:
        return pd.DataFrame()

    def extract_maintenance_history(self) -> pd.DataFrame:
        return pd.DataFrame()

    def extract_spare_parts_catalog(self) -> pd.DataFrame:
        return pd.DataFrame()

    def extract_purchase_orders(self) -> pd.DataFrame:
        return pd.DataFrame()


class ERPConnectorFactory:
    """Factory for creating ERP connectors."""

    _registry = {
        "sap": SAPConnector,
        "oracle": OracleConnector,
        "infor": InforConnector,
    }

    @classmethod
    def create(cls, config: ERPConnectionConfig) -> ERPConnector:
        connector_cls = cls._registry.get(config.system_type.lower())
        if connector_cls is None:
            raise ValueError(f"Unknown ERP system: {config.system_type}. Available: {list(cls._registry.keys())}")
        return connector_cls(config)

    @classmethod
    def register(cls, name: str, connector_cls: type):
        cls._registry[name.lower()] = connector_cls
