"""
AI API Connector - Unified interface for 80+ AI providers.

Usage:
    from ai_connector import Connector
    c = Connector()
    print(c.chat("openai", "Hello!"))
"""
from eazzu.providers.core.connector import Connector
from eazzu.providers.core.registry import PROVIDER_REGISTRY, list_providers
from eazzu.providers.core.config import ConfigManager
from eazzu.providers.core.cache import ResponseCache
from eazzu.providers.core.tracker import UsageTracker
from eazzu.providers.core.failover import FailoverPolicy

__version__ = "1.0.0"
__all__ = [
    "Connector",
    "ConfigManager",
    "ResponseCache",
    "UsageTracker",
    "FailoverPolicy",
    "PROVIDER_REGISTRY",
    "list_providers",
]
