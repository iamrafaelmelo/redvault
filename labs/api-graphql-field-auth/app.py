from __future__ import annotations

import html
import json
import re

from flask import Response, jsonify, request

from labkit import Lab

lab = Lab("LEDGERLINK", accent="#c9a0ff")
app = lab.app

# Minimal GraphQL-like schema. No graphene, no graphql-core: a hand-written
# tokenizer + field resolver so the field-level authorization bug is visible.
TYPES: dict[str, dict[str, dict[str, object]]] = {
    "User": {
        "id": {"type": "ID"},
        "name": {"type": "String"},
        "role": {"type": "String"},
        "finance": {"type": "Finance"},
    },
    "Finance": {
        "balance": {"type": "Float"},
        "currency": {"type": "String"},
        "iban": {"type": "String", "requires": "finance:read"},
        # The sensitive field is intentionally absent from the documented schema
        # and hidden behind the `debug` flag, but still resolvable.
        "flag": {"type": "String", "hidden": True},
    },
    "Query": {
        "user": {"type": "User", "args": {"id": "ID"}},
        "viewer": {"type": "User"},
        "finance": {"type": "Finance", "args": {"userId": "ID"}},
    },
}

USERS: dict[str, dict[str, object]] = {
    "1": {
        "id": "1",
        "name": "Dana Whitfield",
        "role": "analyst",
        "finance": {"balance": 1840.25, "currency": "USD", "iban": "US64 0000 1111 2222"},
    },
    "2": {
        "id": "2",
        "name": "Ops Treasury",
        "role": "admin",
        "finance": {"balance": 920000.0, "currency": "USD", "iban": "US64 9999 8888 7777", "flag": lab.flag("flag")},
    },
}

# Permission model: an object-level permission is enough to resolve the object,
# but individual fields carry their own `requires` entry.
PERMISSIONS = {"user:analyst": {"user:read", "finance:read"}, "service:reporting": {"user:read"}}


def tokenize(query: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"\s*(?:(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<str>\"[^\"]*\")|(?P<num>-?\d+(?:\.\d+)?)|(?P<punct>[{}()\[\]:,!$@]))")
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(query):
        if query[pos:].strip() == "":
            break
        match = pattern.match(query, pos)
        if not match or match.end() == pos:
            raise ValueError(f"unexpected character at {pos}: {query[pos]!r}")
        kind = match.lastgroup or "punct"
        tokens.append((kind, match.group(kind)))
        pos = match.end()
    return tokens


class QueryParseError(ValueError):
    pass


class Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.i = 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self, value: str | None = None) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise QueryParseError("unexpected end of query")
        if value is not None and token[1] != value:
            raise QueryParseError(f"expected {value!r}, got {token[1]!r}")
        self.i += 1
        return token

    def parse(self) -> dict:
        while self.peek() and self.peek()[1] == "query":
            self.take()
            if self.peek() and self.peek()[0] == "name":
                self.take()
        self.take("{")
        fields = self.parse_selection()
        self.take("}")
        return {"fields": fields}

    def parse_selection(self) -> list[dict]:
        fields: list[dict] = []
        while self.peek() and self.peek()[1] != "}":
            kind, name = self.take()
            if name == ",":
                continue
            if kind != "name":
                raise QueryParseError(f"expected field name, got {name!r}")
            node: dict = {"name": name, "args": {}, "fields": []}
            if self.peek() and self.peek()[1] == "(":
                self.take("(")
                while self.peek() and self.peek()[1] != ")":
                    _, arg = self.take()
                    self.take(":")
                    kind_v, value = self.take()
                    node["args"][arg] = value.strip('"') if kind_v == "str" else value
                    if self.peek() and self.peek()[1] == ",":
                        self.take(",")
                self.take(")")
            if self.peek() and self.peek()[1] == "{":
                self.take("{")
                node["fields"] = self.parse_selection()
                self.take("}")
            fields.append(node)
            if self.peek() and self.peek()[1] == ",":
                self.take(",")
        return fields


def visible_schema(include_hidden: bool) -> dict:
    out: dict = {}
    for type_name, fields in TYPES.items():
        rendered: dict[str, object] = {}
        for field_name, meta in fields.items():
            if meta.get("hidden") and not include_hidden:
                continue
            entry = {"type": meta["type"]}
            if meta.get("args"):
                entry["args"] = meta["args"]
            rendered[field_name] = entry
        out[type_name] = rendered
    return out


def resolve(field: dict, parent_type: str, parent_value: object, perms: set[str], errors: list[str]) -> object:
    fields = TYPES.get(parent_type, {})
    meta = fields.get(field["name"])
    if meta is None:
        errors.append(f"Cannot query field '{field['name']}' on type '{parent_type}'.")
        return None
    # VULNERABLE: object-level permission (`finance:read`) is checked, but the
    # per-field `requires` entry of sensitive fields is never enforced.
    if isinstance(parent_value, dict):
        value = parent_value.get(field["name"])
    else:
        value = None
    child_type = meta["type"]
    if child_type in TYPES:
        if value is None:
            return None
        return {node["name"]: resolve(node, child_type, value, perms, errors) for node in field["fields"]}
    return value


def execute(query: str, perms: set[str]) -> dict:
    if "introspectionQuery" in query or "__schema" in query or "__type" in query:
        name = None
        match = re.search(r'__type\s*\(\s*name\s*:\s*"([A-Za-z]+)"', query)
        if match:
            name = match.group(1)
        include_hidden = bool(match and match.group(1) == "Finance")
        schema = visible_schema(include_hidden=include_hidden)
        if name:
            return {"data": {"__type": {"name": name, "fields": [{"name": k, "type": str(v.get("type", "String"))} for k, v in schema.get(name, {}).items()]}}}
        return {"data": {"__schema": {"types": [{"name": k, "fields": [{"name": f} for f in v]} for k, v in schema.items()]}, "queryType": {"name": "Query"}, "description": "Ledgerlink finance graph API"}}
    tree = Parser(tokenize(query)).parse()
    errors: list[str] = []
    data: dict[str, object] = {}
    for node in tree["fields"]:
        root = TYPES["Query"].get(node["name"])
        if root is None:
            errors.append(f"Unknown root field '{node['name']}'.")
            continue
        args = node["args"]
        if node["name"] == "user":
            user = USERS.get(str(args.get("id", "1")))
            data["user"] = None if user is None else {child["name"]: resolve(child, "User", user, perms, errors) for child in node["fields"]}
        elif node["name"] == "viewer":
            user = USERS["1"]
            data["viewer"] = {child["name"]: resolve(child, "User", user, perms, errors) for child in node["fields"]}
        elif node["name"] == "finance":
            user = USERS.get(str(args.get("userId", "1")))
            if "finance:read" not in perms:
                errors.append("Not authorized to read finance objects.")
                data["finance"] = None
            else:
                data["finance"] = None if user is None else {
                    child["name"]: resolve(child, "Finance", user["finance"], perms, errors) for child in node["fields"]
                }
    result: dict[str, object] = {"data": data}
    if errors:
        result["errors"] = errors
    return result


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">LEDGERLINK // GRAPH API</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Explorer</a><a href="/graphql">GraphQL</a><a href="/captured">Log</a>',
    )


@app.get("/")
def index():
    return shell(
        "Graph explorer",
        """<div class="panel"><h2>Endpoint</h2>
        <p><code>POST /graphql</code> with <code>{"query": "{ viewer { id name role } }"}</code>.
        The gateway attaches the analyst permission set <code>user:analyst</code>.</p>
        <p>Introspection is enabled: <code>{"query": "{ __schema { types { name } } }"}</code>.</p>
        <pre>curl -s http://127.0.0.1:PORT/graphql -H 'Content-Type: application/json' \\
  -d '{"query":"{ viewer { id name role finance { currency } } }"}'</pre></div>""",
    )


@app.route("/graphql", methods=["GET", "POST"])
def graphql():
    if request.method == "GET":
        return shell("GraphQL", '<div class="panel">Send a JSON POST with a <code>query</code> key.</div>')
    payload = request.get_json(silent=True)
    query = ""
    if isinstance(payload, dict):
        query = str(payload.get("query", ""))
    elif request.form.get("query"):
        query = request.form.get("query", "")
    if not query:
        return jsonify({"errors": [{"message": "query is required"}]}), 400
    perms = PERMISSIONS["user:analyst"]
    try:
        result = execute(query, perms)
    except (QueryParseError, ValueError) as exc:
        return jsonify({"errors": [{"message": str(exc)}]}), 400
    if lab.flag("flag") in json.dumps(result):
        lab.objective_async("flag", "field-level authorization bypass on finance.flag")
    return Response(json.dumps(result, indent=2), mimetype="application/json")


@app.get("/captured")
def captured():
    body = """<div class="panel"><h2>Gateway log</h2>
    <ul class="list">
      <li><span class="tag">200</span> viewer · analyst permission set applied</li>
      <li><span class="tag">200</span> finance · object-level permission granted</li>
      <li><span class="tag">400</span> malformed query rejected by the parser</li>
    </ul>
    <p class="note">Resolvers log object names only; sensitive field names are masked in operational logs.</p></div>"""
    return shell("Gateway log", body)


if __name__ == "__main__":
    lab.run()