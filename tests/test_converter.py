import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from toonlib import compare, dumps, estimate_tokens, loads


def roundtrip(data):
    toon = dumps(data)
    return loads(toon)


def test_flat_object():
    data = {"name": "Ada", "age": 36, "active": True}
    assert dumps(data) == "name: Ada\nage: 36\nactive: true"
    assert roundtrip(data) == data


def test_nested_object():
    data = {"user": {"name": "Ada", "id": 1}}
    toon = dumps(data)
    assert toon == "user:\n  name: Ada\n  id: 1"
    assert roundtrip(data) == data


def test_primitive_array():
    data = {"tags": ["math", "computing", "logic"]}
    assert dumps(data) == "tags[3]: math,computing,logic"
    assert roundtrip(data) == data


def test_tabular_array():
    data = {
        "users": [
            {"id": 1, "name": "Ada"},
            {"id": 2, "name": "Grace"},
        ]
    }
    expected = "users[2]{id,name}:\n  1,Ada\n  2,Grace"
    assert dumps(data) == expected
    assert roundtrip(data) == data


def test_non_uniform_array():
    data = {"items": [{"a": 1}, {"a": 1, "b": 2}]}
    toon = dumps(data)
    assert roundtrip(data) == data


def test_empty_containers():
    data = {"empty_obj": {}, "empty_list": []}
    assert roundtrip(data) == data


def test_null_and_bool():
    data = {"a": None, "b": True, "c": False}
    assert roundtrip(data) == data


def test_string_needing_quotes():
    data = {"note": "hello, world", "n": "007", "empty": ""}
    toon = dumps(data)
    assert '"hello, world"' in toon
    assert '"007"' in toon
    assert roundtrip(data) == data


def test_root_array_of_objects():
    data = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert roundtrip(data) == data


def test_root_primitive_array():
    data = [1, 2, 3]
    assert dumps(data) == "[3]: 1,2,3"
    assert roundtrip(data) == data


def test_estimate_tokens_basic():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") == 1
    assert estimate_tokens('{"a":1}') == 7  # { " a " : 1 }


def test_compare_tabular_array_saves_tokens():
    data = {"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Grace"}]}
    json_text = json_dumps_compact(data)
    toon_text = dumps(data)
    stats = compare(json_text, toon_text)
    assert stats["toon_tokens"] < stats["json_tokens"]
    assert stats["savings_pct"] > 0


def json_dumps_compact(data):
    import json

    return json.dumps(data, separators=(",", ":"))
