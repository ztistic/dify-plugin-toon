import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from utils.toon_utils import compute_stats, decode_toon


class ToonToJsonAction(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        toon_input = tool_parameters.get('toon_input')
        if toon_input is None or (isinstance(toon_input, str) and not toon_input.strip()):
            yield self.create_text_message(
                'Error: toon_input is empty. Please provide a TOON string to convert.'
            )
            return

        try:
            data = decode_toon(toon_input)
        except Exception as e:
            yield self.create_text_message(f'TOON parsing failed: {e}')
            return

        try:
            yield self.create_text_message(json.dumps(data, ensure_ascii=False, indent=2))
        except (TypeError, ValueError) as e:
            yield self.create_text_message(f'JSON serialization failed: {e}')
