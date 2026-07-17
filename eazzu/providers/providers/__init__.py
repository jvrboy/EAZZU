"""
Provider connectors. Importing this module registers all providers via the
@register_provider decorator.
"""
# Import order registers all providers into PROVIDER_REGISTRY
from eazzu.providers.providers import openai_compatible  # noqa: F401
from eazzu.providers.providers import llm_providers  # noqa: F401
from eazzu.providers.providers import cloud_providers  # noqa: F401
from eazzu.providers.providers import aggregators  # noqa: F401
from eazzu.providers.providers import audio_providers  # noqa: F401
from eazzu.providers.providers import image_providers  # noqa: F401
from eazzu.providers.providers import search_providers  # noqa: F401
from eazzu.providers.providers import embedding_providers  # noqa: F401
from eazzu.providers.providers import custom  # noqa: F401
