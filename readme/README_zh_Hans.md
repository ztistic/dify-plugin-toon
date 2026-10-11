# Dify TOON 转换器插件（中文说明）

> 本文件为中文补充说明，市场发布以英文 [README.md](../README.md) 为准。

在 **JSON** 与 **TOON**（Token-Oriented Object Notation）之间双向转换的 Dify 插件。
TOON 是面向 LLM 的紧凑数据格式，通过去掉冗余引号、大括号和重复键名，
通常可比 JSON 节省 **30-60%** 的 Token。

底层采用 [toon-format](https://pypi.org/project/toon-format/)——TOON 规范的
**官方 Python 实现**（toon-format/toon-python），通过全部官方一致性测试，
对所有 JSON 兼容值（含嵌套结构、嵌套字段组表格）保证无损往返。
解码时按规范从表格头部自动识别分隔符，无需手动指定。

## 工具

### JSON to TOON

| 参数         | 类型     | 必填 | 说明                                        |
|--------------|----------|------|---------------------------------------------|
| `json_input` | `string` | 是   | 待转换的 JSON 字符串                        |
| `delimiter`  | `select` | 否   | 分隔符：`comma`（默认）/ `tab` / `pipe`     |

返回一个 JSON 消息，包含 `toon` 输出文本以及压缩统计
（`original_chars`、`toon_chars`、`compression_ratio`、`savings_percent`）。

### TOON to JSON

| 参数         | 类型     | 必填 | 说明                     |
|--------------|----------|------|--------------------------|
| `toon_input` | `string` | 是   | 待转换的 TOON 字符串     |

返回 `ensure_ascii=False`、`indent=2` 格式化后的 JSON 字符串。
JSON → TOON → JSON 往返转换保持一致。

## 错误处理

所有无效输入（空字符串、非法 JSON、非法 TOON）都会返回友好的英文错误消息，
不会抛出未捕获异常。
