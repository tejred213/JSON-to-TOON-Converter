"""Core JSON <-> TOON conversion logic.

TOON (Token-Oriented Object Notation) is an indentation-based format for
representing JSON-like data with far less punctuation, aimed at shrinking
token counts when structured data is passed to an LLM. This module is a
from-scratch implementation covering the common cases:

  - objects (key: value, nested blocks)
  - arrays of primitives -> inline comma list with a length marker
  - arrays of uniform objects -> tabular block (header + rows)
  - non-uniform arrays -> YAML-style "- " list items

Deeply nested arrays-of-arrays are supported on a best-effort basis; the
test suite documents what round-trips exactly.
"""

import re

_SCALAR_QUOTE_CHARS = set(':,{}[]#"\n')


def dumps(data, indent=2):
    lines = []
    if isinstance(data, dict):
        _dump_object(data, lines, 0, indent)
    elif isinstance(data, list):
        _dump_root_array(data, lines, indent)
    else:
        lines.append(_format_scalar(data))
    return "\n".join(lines)


def loads(s):
    raw_lines = [line for line in s.split("\n") if line.strip() != ""]
    lines = [(len(line) - len(line.lstrip(" ")), line.strip()) for line in raw_lines]
    if not lines:
        return None
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value


# ---------------------------------------------------------------------------
# dumping
# ---------------------------------------------------------------------------

def _format_scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _format_string(value)
    raise TypeError(f"Cannot serialize value of type {type(value)!r} to TOON")


def _needs_quotes(s):
    if s == "":
        return True
    if s.strip() != s:
        return True
    if s in ("true", "false", "null"):
        return True
    if any(ch in _SCALAR_QUOTE_CHARS for ch in s):
        return True
    try:
        float(s)
        return True
    except ValueError:
        pass
    return False


def _format_string(s):
    if _needs_quotes(s):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return s


def _format_key(key):
    key = str(key)
    return _format_string(key) if _needs_quotes(key) else key


def _dump_object(obj, lines, level, indent_size):
    pad = " " * (level * indent_size)
    for key, value in obj.items():
        key_str = _format_key(key)
        if isinstance(value, dict):
            if not value:
                lines.append(f"{pad}{key_str}: {{}}")
            else:
                lines.append(f"{pad}{key_str}:")
                _dump_object(value, lines, level + 1, indent_size)
        elif isinstance(value, list):
            _dump_array(key_str, value, lines, level, indent_size)
        else:
            lines.append(f"{pad}{key_str}: {_format_scalar(value)}")


def _is_uniform_object_array(arr):
    if not arr or not all(isinstance(v, dict) for v in arr):
        return False
    keys0 = list(arr[0].keys())
    if not keys0:
        return False
    for item in arr:
        if list(item.keys()) != keys0:
            return False
        if any(isinstance(v, (dict, list)) for v in item.values()):
            return False
    return True


def _dump_array(key_str, arr, lines, level, indent_size):
    pad = " " * (level * indent_size)
    n = len(arr)
    if n == 0:
        lines.append(f"{pad}{key_str}[0]:")
        return
    if all(not isinstance(v, (dict, list)) for v in arr):
        values = ",".join(_format_scalar(v) for v in arr)
        lines.append(f"{pad}{key_str}[{n}]: {values}")
        return
    if _is_uniform_object_array(arr):
        keys0 = list(arr[0].keys())
        fields = ",".join(_format_key(k) for k in keys0)
        lines.append(f"{pad}{key_str}[{n}]{{{fields}}}:")
        row_pad = " " * ((level + 1) * indent_size)
        for row in arr:
            values = ",".join(_format_scalar(row[k]) for k in keys0)
            lines.append(f"{row_pad}{values}")
        return
    lines.append(f"{pad}{key_str}[{n}]:")
    for item in arr:
        _dump_list_item(item, lines, level + 1, indent_size)


def _dump_root_array(arr, lines, indent_size):
    n = len(arr)
    if n == 0:
        lines.append("[0]:")
        return
    if all(not isinstance(v, (dict, list)) for v in arr):
        values = ",".join(_format_scalar(v) for v in arr)
        lines.append(f"[{n}]: {values}")
        return
    if _is_uniform_object_array(arr):
        keys0 = list(arr[0].keys())
        fields = ",".join(_format_key(k) for k in keys0)
        lines.append(f"[{n}]{{{fields}}}:")
        row_pad = " " * indent_size
        for row in arr:
            values = ",".join(_format_scalar(row[k]) for k in keys0)
            lines.append(f"{row_pad}{values}")
        return
    lines.append(f"[{n}]:")
    for item in arr:
        _dump_list_item(item, lines, 1, indent_size)


def _dump_list_item(item, lines, level, indent_size):
    pad = " " * (level * indent_size)
    if isinstance(item, dict):
        if not item:
            lines.append(f"{pad}- {{}}")
            return
        sub_lines = []
        _dump_object(item, sub_lines, 0, indent_size)
        for i, sub_line in enumerate(sub_lines):
            prefix = "- " if i == 0 else "  "
            lines.append(f"{pad}{prefix}{sub_line}")
    elif isinstance(item, list):
        if not item:
            lines.append(f"{pad}- []")
            return
        lines.append(f"{pad}-")
        for sub_item in item:
            _dump_list_item(sub_item, lines, level + 1, indent_size)
    else:
        lines.append(f"{pad}- {_format_scalar(item)}")


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

_KEY_LINE_RE = re.compile(r'^(".*?"|[^:\[]+?)(\[(\d+)\])?(\{(.+?)\})?:\s*(.*)$')


def _split_values(s):
    values = []
    current = ""
    in_quotes = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '"' and (i == 0 or s[i - 1] != "\\"):
            in_quotes = not in_quotes
            current += ch
        elif ch == "," and not in_quotes:
            values.append(current)
            current = ""
        else:
            current += ch
        i += 1
    values.append(current)
    return [v.strip() for v in values]


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        inner = s[1:-1]
        return inner.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    return s


def _parse_scalar(s):
    s = s.strip()
    if s == "null":
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return _unquote(s)
    if re.match(r"^-?\d+$", s):
        return int(s)
    try:
        return float(s)
    except ValueError:
        return s


_ROOT_ARRAY_RE = re.compile(r'^\[(\d+)\](\{(.+?)\})?:\s*(.*)$')


def _parse_block(lines, idx, indent):
    if idx >= len(lines):
        return {}, idx
    _, content = lines[idx]
    if content == "-" or content.startswith("- "):
        return _parse_list(lines, idx, indent)
    if _ROOT_ARRAY_RE.match(content):
        return _parse_root_array(lines, idx, indent)
    return _parse_object(lines, idx, indent)


def _parse_root_array(lines, idx, indent):
    _, content = lines[idx]
    count, _, fields, rest = _ROOT_ARRAY_RE.match(content).groups()
    n = int(count)
    idx += 1

    if fields is not None:
        field_names = [_unquote(f.strip()) for f in fields.split(",")]
        rows = []
        for _ in range(n):
            _, row_content = lines[idx]
            values = _split_values(row_content)
            rows.append({fn: _parse_scalar(v) for fn, v in zip(field_names, values)})
            idx += 1
        return rows, idx

    if rest.strip() != "":
        values = _split_values(rest)
        return [_parse_scalar(v) for v in values], idx

    if n == 0:
        return [], idx

    item_indent = lines[idx][0]
    return _parse_list(lines, idx, item_indent)


def _parse_object(lines, idx, indent):
    obj = {}
    while idx < len(lines):
        line_indent, content = lines[idx]
        if line_indent != indent:
            break
        match = _KEY_LINE_RE.match(content)
        if not match:
            idx += 1
            continue
        key_raw, _, count, _, fields, rest = match.groups()
        key = _unquote(key_raw.strip())

        if fields is not None:
            field_names = [_unquote(f.strip()) for f in fields.split(",")]
            n = int(count)
            rows = []
            idx += 1
            for _ in range(n):
                _, row_content = lines[idx]
                values = _split_values(row_content)
                rows.append({fn: _parse_scalar(v) for fn, v in zip(field_names, values)})
                idx += 1
            obj[key] = rows
            continue

        if count is not None:
            n = int(count)
            values = _split_values(rest) if rest.strip() != "" else []
            if rest.strip() == "" and n > 0:
                idx += 1
                item_indent = lines[idx][0]
                items, idx = _parse_list(lines, idx, item_indent)
                obj[key] = items
            else:
                obj[key] = [_parse_scalar(v) for v in values]
                idx += 1
            continue

        rest_stripped = rest.strip()
        if rest_stripped == "{}":
            obj[key] = {}
            idx += 1
        elif rest_stripped == "[]":
            obj[key] = []
            idx += 1
        elif rest_stripped != "":
            obj[key] = _parse_scalar(rest_stripped)
            idx += 1
        else:
            idx += 1
            if idx < len(lines) and lines[idx][0] > line_indent:
                child_indent = lines[idx][0]
                value, idx = _parse_block(lines, idx, child_indent)
                obj[key] = value
            else:
                obj[key] = {}
    return obj, idx


def _parse_list(lines, idx, indent):
    items = []
    while idx < len(lines):
        line_indent, content = lines[idx]
        if line_indent != indent or not (content == "-" or content.startswith("- ")):
            break
        rest = content[2:] if content.startswith("- ") else ""

        if rest == "":
            idx += 1
            if idx < len(lines) and lines[idx][0] > indent:
                value, idx = _parse_block(lines, idx, lines[idx][0])
                items.append(value)
            else:
                items.append(None)
            continue

        if rest == "{}":
            items.append({})
            idx += 1
            continue
        if rest == "[]":
            items.append([])
            idx += 1
            continue

        if _KEY_LINE_RE.match(rest) and not _is_bare_scalar(rest):
            virtual_indent = indent + 2
            virtual_lines = [(virtual_indent, rest)]
            j = idx + 1
            while j < len(lines) and lines[j][0] >= virtual_indent and not (
                lines[j][0] == indent and (lines[j][1] == "-" or lines[j][1].startswith("- "))
            ):
                virtual_lines.append(lines[j])
                j += 1
            obj, _ = _parse_object(virtual_lines, 0, virtual_indent)
            items.append(obj)
            idx = j
            continue

        items.append(_parse_scalar(rest))
        idx += 1
    return items, idx


def _is_bare_scalar(s):
    """Distinguish 'true'/'null'/a quoted string from an actual 'key: value' pair."""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return True
    return s in ("true", "false", "null") or ":" not in s
