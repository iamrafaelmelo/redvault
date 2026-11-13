from __future__ import annotations

import html
import re
import secrets

from flask import jsonify, request, session

from labkit import Lab

lab = Lab("SENTRY DOCS", accent="#5aa9ff")
app = lab.app

# The admin password is generated per process and never disclosed. The
# document matcher is the only authentication routine.
USERS = [
    {"username": "analyst", "password": "analyst123", "role": "analyst", "display": "Mira Chen"},
    {"username": "admin", "password": secrets.token_urlsafe(24), "role": "admin", "display": "Vault Administrator"},
]


def _compare(value, operator: str, operand) -> bool:
    if operator == "$eq":
        return value == operand
    if operator == "$ne":
        return value != operand
    if operator == "$gt":
        try:
            return value > operand
        except TypeError:
            return False
    if operator == "$gte":
        try:
            return value >= operand
        except TypeError:
            return False
    if operator == "$lt":
        try:
            return value < operand
        except TypeError:
            return False
    if operator == "$lte":
        try:
            return value <= operand
        except TypeError:
            return False
    if operator == "$in":
        return isinstance(operand, list) and value in operand
    if operator == "$nin":
        return isinstance(operand, list) and value not in operand
    if operator == "$regex":
        try:
            return re.search(str(operand), str(value)) is not None
        except re.error:
            return False
    if operator == "$not":
        return not _matches(value, operand)
    return False


def _matches(value, condition) -> bool:
    """Evaluate one document field against a very small Mongo-style query."""
    if isinstance(condition, dict):
        return all(_compare(value, op, operand) for op, operand in condition.items())
    return value == condition


def _credentials() -> tuple[object, object]:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data.get("username"), data.get("password")
    return request.form.get("username"), request.form.get("password")


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">SENTRY // IDENTITY DOCUMENTS</div><h1>{title}</h1>'
        '<p>Internal access console for the document-store identity service.</p></div>' + body,
        nav='<a href="/">Sign in</a><a href="/health">Health</a>',
    )


@app.get("/")
def index():
    return shell(
        "Identity gateway",
        """
        <div class="grid">
          <div class="panel">
            <h2>Operator sign-in</h2>
            <form id="login">
              <label>Username</label><input name="username" autocomplete="username" placeholder="analyst">
              <label>Password</label><input name="password" type="password" autocomplete="current-password">
              <p><button type="submit">Authenticate</button></p>
            </form>
            <pre id="result" class="dim">No request sent.</pre>
          </div>
          <div class="panel">
            <h2>Document matcher</h2>
            <p>Credentials are stored as JSON documents. The gateway evaluates the submitted fields with a compact query matcher that understands the usual comparison operators.</p>
            <p class="note">The administrator document is seeded with a random password during deployment. Operators authenticate with their own account.</p>
            <p class="dim mono">POST /api/login · application/json</p>
          </div>
        </div>
        <script>
        const form = document.getElementById('login');
        form.addEventListener('submit', async (event) => {
          event.preventDefault();
          const result = document.getElementById('result');
          result.textContent = 'Checking...';
          try {
            const response = await fetch('/api/login', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({username: form.username.value, password: form.password.value})
            });
            const data = await response.json();
            result.textContent = JSON.stringify(data, null, 2);
          } catch (error) {
            result.textContent = 'Request failed: ' + error;
          }
        });
        </script>
        """,
    )


@app.post("/api/login")
def api_login():
    username_query, password_query = _credentials()
    if username_query is None or password_query is None:
        return jsonify({"ok": False, "error": "username and password are required"}), 400

    for user in USERS:
        if _matches(user["username"], username_query) and _matches(user["password"], password_query):
            session["user"] = user["username"]
            response = {"ok": True, "user": user["username"], "role": user["role"], "display": user["display"]}
            if user["role"] == "admin":
                response["flag"] = lab.flag("flag")
            return jsonify(response)

    return jsonify({"ok": False, "error": "invalid credentials"}), 401


@app.get("/logout")
def logout():
    session.clear()
    return lab.redirect("/")


@app.errorhandler(404)
def not_found(_error):
    return shell("Not found", '<div class="flash err">No such identity endpoint.</div>'), 404


if __name__ == "__main__":
    lab.run()
