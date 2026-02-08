"""
Anomaly Config Service
======================

Service for managing anomaly detection configuration in the database.
Handles reading/writing config parameters with dot notation for nested fields.
"""

from dataclasses import fields, is_dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomaly.config import AnomalyConfig, QuantileParams, ZScoreParams
from app.models import AnomalyConfigEntry


# Type mapping for config fields
TYPE_MAP = {
    int: 'int',
    float: 'float',
    bool: 'bool',
    str: 'str',
}


def get_type_name(value: Any) -> str:
    """Get the type name for a value."""
    for py_type, type_name in TYPE_MAP.items():
        if isinstance(value, py_type):
            return type_name
    return 'str'


def parse_value(value_str: str, type_name: str) -> Any:
    """Parse a string value to the appropriate type."""
    if type_name == 'int':
        return int(value_str)
    elif type_name == 'float':
        return float(value_str)
    elif type_name == 'bool':
        return value_str.lower() in ('true', '1', 'yes')
    return value_str


def flatten_config(config: AnomalyConfig) -> Dict[str, Tuple[str, Any]]:
    """
    Flatten an AnomalyConfig into a dict of key -> (type, value) pairs.
    
    Nested dataclasses use dot notation (e.g., 'quantile_params.baseline_percentile').
    
    Args:
        config: AnomalyConfig instance
        
    Returns:
        Dict mapping keys to (type_name, value) tuples
    """
    result = {}
    
    for field in fields(config):
        value = getattr(config, field.name)
        
        if is_dataclass(value):
            # Handle nested dataclass
            for nested_field in fields(value):
                nested_value = getattr(value, nested_field.name)
                key = f"{field.name}.{nested_field.name}"
                result[key] = (get_type_name(nested_value), nested_value)
        else:
            result[field.name] = (get_type_name(value), value)
    
    return result


def get_valid_keys() -> Dict[str, str]:
    """
    Get all valid configuration keys and their types.
    
    Returns:
        Dict mapping key names to type names
    """
    default_config = AnomalyConfig()
    flattened = flatten_config(default_config)
    return {k: v[0] for k, v in flattened.items()}


def get_default_values() -> Dict[str, Tuple[str, Any]]:
    """
    Get all default configuration values.
    
    Returns:
        Dict mapping key names to (type, value) tuples
    """
    default_config = AnomalyConfig()
    return flatten_config(default_config)


class AnomalyConfigService:
    """
    Service for managing anomaly detection configuration.
    
    Reads and writes configuration parameters to the anomaly_config table.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with a database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self._valid_keys = get_valid_keys()
        self._defaults = get_default_values()
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all configuration entries.
        
        Returns entries for all valid keys, using defaults where not set in DB.
        
        Returns:
            List of config entries with key, type, value, and is_default flag
        """
        # Get all DB entries
        stmt = select(AnomalyConfigEntry)
        result = await self.session.execute(stmt)
        db_entries = {entry.key: entry for entry in result.scalars().all()}
        
        # Build response with all valid keys
        response = []
        for key, (type_name, default_value) in self._defaults.items():
            if key in db_entries:
                entry = db_entries[key]
                response.append({
                    'key': key,
                    'type': entry.type,
                    'value': entry.value,
                    'is_default': False,
                })
            else:
                response.append({
                    'key': key,
                    'type': type_name,
                    'value': str(default_value),
                    'is_default': True,
                })
        
        return response
    
    async def get_value(self, key: str) -> Optional[Any]:
        """
        Get a single configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Typed value if found in DB or default, None if invalid key
        """
        if key not in self._valid_keys:
            return None
        
        stmt = select(AnomalyConfigEntry).where(AnomalyConfigEntry.key == key)
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if entry:
            return parse_value(entry.value, entry.type)
        
        # Return default
        _, default_value = self._defaults[key]
        return default_value
    
    async def set_value(self, key: str, value: str) -> Optional[Dict[str, Any]]:
        """
        Set a configuration value.
        
        Validates the key and value, then inserts or updates the DB entry.
        
        Args:
            key: Configuration key
            value: String value to set
            
        Returns:
            Updated entry dict if successful, None if invalid key
            
        Raises:
            ValueError: If value cannot be parsed to the expected type
        """
        if key not in self._valid_keys:
            return None
        
        type_name = self._valid_keys[key]
        
        # Validate value can be parsed
        try:
            parsed = parse_value(value, type_name)
            # Re-stringify for storage
            value_str = str(parsed).lower() if type_name == 'bool' else str(parsed)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value '{value}' for type {type_name}: {e}")
        
        # Upsert the entry
        stmt = select(AnomalyConfigEntry).where(AnomalyConfigEntry.key == key)
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if entry:
            entry.value = value_str
            entry.type = type_name
        else:
            entry = AnomalyConfigEntry(
                key=key,
                type=type_name,
                value=value_str,
            )
            self.session.add(entry)
        
        await self.session.flush()
        await self.session.refresh(entry)
        
        return {
            'key': entry.key,
            'type': entry.type,
            'value': entry.value,
            'is_default': False,
        }
    
    async def reset_to_default(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Reset a configuration value to its default.
        
        Deletes the DB entry for the key, causing default to be used.
        
        Args:
            key: Configuration key
            
        Returns:
            Default entry dict if successful, None if invalid key
        """
        if key not in self._valid_keys:
            return None
        
        stmt = select(AnomalyConfigEntry).where(AnomalyConfigEntry.key == key)
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if entry:
            await self.session.delete(entry)
            await self.session.flush()
        
        type_name, default_value = self._defaults[key]
        return {
            'key': key,
            'type': type_name,
            'value': str(default_value),
            'is_default': True,
        }
    
    async def build_anomaly_config(self) -> AnomalyConfig:
        """
        Build an AnomalyConfig instance from database values.
        
        Reads all configuration from DB, falling back to defaults where not set.
        
        Returns:
            AnomalyConfig instance with values from DB
        """
        # Get all DB entries
        stmt = select(AnomalyConfigEntry)
        result = await self.session.execute(stmt)
        db_entries = {entry.key: entry for entry in result.scalars().all()}
        
        # Build kwargs for top-level fields
        config_kwargs = {}
        quantile_kwargs = {}
        zscore_kwargs = {}
        
        for key, (type_name, default_value) in self._defaults.items():
            if key in db_entries:
                entry = db_entries[key]
                value = parse_value(entry.value, entry.type)
            else:
                value = default_value
            
            if '.' in key:
                prefix, field_name = key.split('.', 1)
                if prefix == 'quantile_params':
                    quantile_kwargs[field_name] = value
                elif prefix == 'zscore_params':
                    zscore_kwargs[field_name] = value
            else:
                config_kwargs[key] = value
        
        # Build nested params
        if quantile_kwargs:
            config_kwargs['quantile_params'] = QuantileParams(**quantile_kwargs)
        if zscore_kwargs:
            config_kwargs['zscore_params'] = ZScoreParams(**zscore_kwargs)
        
        return AnomalyConfig(**config_kwargs)
