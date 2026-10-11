import json
import os

import pytest

from dify_plugin.entities.tool import ToolInvokeMessage
from tools.json_to_toon import JsonToToonAction
from tools.toon_to_json import ToonToJsonAction
from utils.toon_utils import compute_stats, decode_toon, encode_toon, normalize_delimiter


def make_tool(cls):
    """构造工具实例，绕过 Tool.__init__，仅提供测试所需的 runtime/response_type。"""
    tool = cls.__new__(cls)
    tool.runtime = type('Runtime', (), {'credentials': {}})()
    tool.response_type = ToolInvokeMessage
    return tool


def message_text(message) -> str:
    return getattr(message.message, 'text', message.message)


def message_json(message) -> dict:
    return message.message.json_object


class TestNormalizeDelimiter:
    @pytest.mark.parametrize(
        'value,expected',
        [
            (None, 'comma'),
            ('', 'comma'),
            ('comma', 'comma'),
            (',', 'comma'),
            ('tab', 'tab'),
            ('\\t', 'tab'),
            ('\t', 'tab'),
            ('pipe', 'pipe'),
            ('|', 'pipe'),
            ('PIPE', 'pipe'),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_delimiter(value) == expected

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            normalize_delimiter('semicolon')


class TestComputeStats:
    def test_ratio_calculation(self):
        stats = compute_stats('a' * 1000, 'a' * 400)
        assert stats['original_chars'] == 1000
        assert stats['toon_chars'] == 400
        assert stats['compression_ratio'] == 0.6
        assert stats['savings_percent'] == 60.0

    def test_empty_original(self):
        stats = compute_stats('', 'abc')
        assert stats['compression_ratio'] == 0.0


class TestRoundTrip:
    @pytest.mark.parametrize(
        'data',
        [
            {'name': 'Alice', 'age': 30, 'active': True},
            {'nested': {'a': [1, 2, 3], 'b': None}, 'flag': False},
            [1, 'two', 3.5, True, None],
            'plain string',
            42,
            {'unicode': '中文内容', 'emoji': '🎉'},
            {'items': [{'id': 1, 'name': 'Ada'}, {'id': 2, 'name': 'Bob'}]},
            [{'a': {'b': 1}}],
            [{'a': [1, 2]}],
            [[1, 2], [3, 4]],
            [{'a': [{'b': 1}]}],
            {'x': {'y': {'z': [1, {'w': 2}]}}},
            {'forecast': [{'day': 'Mon', 'temp': {'min': -2, 'max': 4}}, {'day': 'Tue', 'temp': {'min': 1, 'max': 7}}]},
        ],
    )
    @pytest.mark.parametrize('delimiter', ['comma', 'tab', 'pipe'])
    def test_json_to_toon_to_json(self, data, delimiter):
        toon_str = encode_toon(data, delimiter)
        assert decode_toon(toon_str) == data

    def test_official_weather_example_with_field_groups(self):
        # 官方规范 README 的样例：嵌套字段组 temp{min,max} 折叠进表格头
        data = {
            'location': {'city': 'Berlin', 'country': 'DE', 'units': 'metric'},
            'alerts': ['frost', 'wind'],
            'forecast': [
                {'day': 'Mon', 'temp': {'min': -2, 'max': 4}, 'condition': 'snow', 'rainChance': 80},
                {'day': 'Tue', 'temp': {'min': 1, 'max': 7}, 'condition': 'cloudy', 'rainChance': 20},
            ],
        }
        toon_str = encode_toon(data)
        assert 'forecast[2]{day,temp{min,max},condition,rainChance}:' in toon_str
        assert 'Mon,-2,4,snow,80' in toon_str
        assert decode_toon(toon_str) == data

    def test_official_benchmark_github_repos(self):
        # 官方 toon 仓库 benchmarks/data/github-repos.json（MIT 许可）：
        # Top 100 GitHub 仓库，官方基准声称较 JSON 省约 42% token（字符口径约 38%）
        fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'github-repos.json')
        with open(fixture, encoding='utf-8') as f:
            data = json.load(f)
        payload = json.dumps(data, ensure_ascii=False)
        toon_str = encode_toon(data)
        # 百条同构记录折叠为单张表：字段名只声明一次
        assert toon_str.startswith('[100]{id,name,repo,description,')
        assert decode_toon(toon_str) == data
        stats = compute_stats(payload, toon_str)
        assert stats['savings_percent'] > 35


class TestJsonToToonAction:
    def test_basic_object(self):
        tool = make_tool(JsonToToonAction)
        msgs = list(tool._invoke({'json_input': '{"name": "Alice", "age": 30, "active": true}'}))
        # text 输出为纯 TOON，json 输出携带统计
        assert len(msgs) == 2
        assert 'name: Alice' in message_text(msgs[0])
        result = message_json(msgs[1])
        assert result['toon'] == message_text(msgs[0])
        assert result['original_chars'] == len('{"name": "Alice", "age": 30, "active": true}')
        assert result['toon_chars'] == len(result['toon'])
        assert 0 < result['compression_ratio'] < 1

    def test_tabular_array_declares_fields_once(self):
        tool = make_tool(JsonToToonAction)
        payload = json.dumps(
            {'users': [{'id': 1, 'name': 'Ada', 'role': 'admin'}, {'id': 2, 'name': 'Bob', 'role': 'user'}]}
        )
        msgs = list(tool._invoke({'json_input': payload}))
        toon = message_json(msgs[1])['toon']
        assert 'users[2]{id,name,role}:' in toon
        # 字段名只出现一次（在 header 中），数据以紧凑表格行排列
        assert toon.count('id') == 1
        assert '1,Ada,admin' in toon
        assert '2,Bob,user' in toon
        assert message_text(msgs[0]) == toon

    @pytest.mark.parametrize(
        'delimiter,sep',
        [('tab', '\t'), ('pipe', '|')],
    )
    def test_custom_delimiter(self, delimiter, sep):
        tool = make_tool(JsonToToonAction)
        payload = json.dumps([{'id': 1, 'name': 'Ada'}])
        msgs = list(tool._invoke({'json_input': payload, 'delimiter': delimiter}))
        toon = message_json(msgs[1])['toon']
        assert f'1{sep}Ada' in toon

    def test_nested_in_array_roundtrips_in_spec_dialect(self):
        # 官方实现对数组内嵌套结构也保持无损（字段组折叠）
        tool = make_tool(JsonToToonAction)
        data = {'forecast': [{'day': 'Mon', 'temp': {'min': -2, 'max': 4}}]}
        msgs = list(tool._invoke({'json_input': json.dumps(data)}))
        assert decode_toon(message_json(msgs[1])['toon']) == data

    def test_invalid_json_returns_friendly_error(self):
        tool = make_tool(JsonToToonAction)
        msgs = list(tool._invoke({'json_input': '{invalid}'}))
        assert len(msgs) == 1
        text = message_text(msgs[0])
        assert text.startswith('JSON parsing failed:')

    @pytest.mark.parametrize('bad_input', ['', '   ', None])
    def test_empty_input_returns_friendly_error(self, bad_input):
        tool = make_tool(JsonToToonAction)
        msgs = list(tool._invoke({'json_input': bad_input}))
        assert len(msgs) == 1
        assert message_text(msgs[0]).startswith('Error:')

    def test_invalid_delimiter_returns_friendly_error(self):
        tool = make_tool(JsonToToonAction)
        msgs = list(tool._invoke({'json_input': '{"a": 1}', 'delimiter': 'semicolon'}))
        assert len(msgs) == 1
        assert message_text(msgs[0]).startswith('Error:')

    def test_non_finite_number_normalized_to_null(self):
        # json.loads 接受 Infinity/NaN；TOON 规范将非有限数字归一化为 null，转换照常成功
        tool = make_tool(JsonToToonAction)
        msgs = list(tool._invoke({'json_input': '{"v": Infinity}'}))
        assert len(msgs) == 2
        assert message_json(msgs[1])['toon'] == 'v: null'

    def test_non_string_input_normalized(self):
        tool = make_tool(JsonToToonAction)
        msgs = list(tool._invoke({'json_input': {'a': 1}}))
        assert len(msgs) == 2
        assert message_json(msgs[1])['toon'] == encode_toon({'a': 1})


class TestToonToJsonAction:
    def test_basic_object(self):
        tool = make_tool(ToonToJsonAction)
        msgs = list(tool._invoke({'toon_input': 'name: Alice\nage: 30'}))
        # text 输出为格式化 JSON 字符串，json 输出为解析后的对象
        assert len(msgs) == 2
        text = message_text(msgs[0])
        assert json.loads(text) == {'name': 'Alice', 'age': 30}
        assert text.startswith('{\n  ')  # indent=2
        assert message_json(msgs[1]) == {'name': 'Alice', 'age': 30}

    def test_unicode_preserved(self):
        tool = make_tool(ToonToJsonAction)
        msgs = list(tool._invoke({'toon_input': 'city: 北京'}))
        assert '北京' in message_text(msgs[0])
        assert '\\u' not in message_text(msgs[0])
        assert message_json(msgs[1]) == {'city': '北京'}

    def test_tabular_toon(self):
        tool = make_tool(ToonToJsonAction)
        toon = 'users[2]{id,name,role}:\n  1,Ada,admin\n  2,Bob,user'
        msgs = list(tool._invoke({'toon_input': toon}))
        expected = {'users': [{'id': 1, 'name': 'Ada', 'role': 'admin'}, {'id': 2, 'name': 'Bob', 'role': 'user'}]}
        assert json.loads(message_text(msgs[0])) == expected
        assert message_json(msgs[1]) == expected

    def test_tab_delimiter_auto_detected_from_header(self):
        # 规范要求分隔符声明在头部 [N<TAB>]，解码器自动识别，无需提示
        tool = make_tool(ToonToJsonAction)
        toon = 'users[2\t]{id\tname}:\n  1\tAda\n  2\tBob'
        msgs = list(tool._invoke({'toon_input': toon}))
        expected = {'users': [{'id': 1, 'name': 'Ada'}, {'id': 2, 'name': 'Bob'}]}
        assert json.loads(message_text(msgs[0])) == expected
        assert message_json(msgs[1]) == expected

    def test_nested_field_groups(self):
        # 官方 README 天气样例的 TOON 文本（含嵌套字段组）可直接解码
        tool = make_tool(ToonToJsonAction)
        toon = 'forecast[2]{day,temp{min,max},condition}:\n  Mon,-2,4,snow\n  Tue,1,7,cloudy'
        msgs = list(tool._invoke({'toon_input': toon}))
        expected = {
            'forecast': [
                {'day': 'Mon', 'temp': {'min': -2, 'max': 4}, 'condition': 'snow'},
                {'day': 'Tue', 'temp': {'min': 1, 'max': 7}, 'condition': 'cloudy'},
            ]
        }
        assert json.loads(message_text(msgs[0])) == expected
        assert message_json(msgs[1]) == expected

    def test_invalid_toon_returns_friendly_error(self):
        tool = make_tool(ToonToJsonAction)
        msgs = list(tool._invoke({'toon_input': 'a[not-a-number]{b}:\n  ???'}))
        assert len(msgs) == 1
        assert message_text(msgs[0]).startswith('TOON parsing failed:')

    @pytest.mark.parametrize('bad_input', ['', '   ', None])
    def test_empty_input_returns_friendly_error(self, bad_input):
        tool = make_tool(ToonToJsonAction)
        msgs = list(tool._invoke({'toon_input': bad_input}))
        assert len(msgs) == 1
        assert message_text(msgs[0]).startswith('Error:')
