from typing import Any

from dify_plugin import ToolProvider


class ToonConverterToolProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # This plugin performs local in-memory conversion only and requires
        # no credentials, so there is nothing to validate.
        return
