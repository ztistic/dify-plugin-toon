import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from utils.toon_utils import compute_stats, encode_toon, normalize_delimiter


class JsonToToonAction(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        json_input = tool_parameters.get('json_input')
        if json_input is None or (isinstance(json_input, str) and not json_input.strip()):
            yield self.create_text_message(
                'Error: json_input is empty. Please provide a JSON string to convert.'
            )
            return

        # If a non-string value arrives (e.g. an already-decoded object),
        # serialize it back to JSON text first.
        if not isinstance(json_input, str):
            json_input = json.dumps(json_input, ensure_ascii=False)

        try:
            delimiter = normalize_delimiter(tool_parameters.get('delimiter'))
        except ValueError as e:
            yield self.create_text_message(f'Error: {e}')
            return

        try:
            data = json.loads(json_input)
        except json.JSONDecodeError as e:
            yield self.create_text_message(f'JSON parsing failed: {e}')
            return

        try:
            toon_str = encode_toon(data, delimiter)
        except Exception as e:
            yield self.create_text_message(f'TOON encoding failed: {e}')
            return

        result = {
            'toon': toon_str,
            **compute_stats(json_input, toon_str),
        }
        yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))
