from __future__ import annotations

from flask import jsonify

from labkit import Lab

lab = Lab("TEAMSPACE API", accent="#5b8ff9")
app = lab.app

TEAM = [
    {"id": 1, "name": "Maya Chen", "role": "Research", "email": "maya@teamspace.local", "public_bio": "Maps signal in noise."},
    {"id": 2, "name": "Ravi Shah", "role": "Engineering", "email": "ravi@teamspace.local", "public_bio": "Builds the boring parts well."},
    {"id": 3, "name": "Nora Vale", "role": "Operations", "email": "nora@teamspace.local", "public_bio": "Keeps the lights on."},
]


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">TEAMSPACE // DIRECTORY</div><h1>{title}</h1></div>{body}', nav='<a href="/">Directory</a><a href="/api/v1/team">Team API</a>')


@app.get("/")
def index():
    cards = "".join(
        f'<div class="panel"><h2>{member["name"]}</h2><p>{member["public_bio"]}</p><span class="tag">{member["role"]}</span></div>'
        for member in TEAM
    )
    return shell(
        "Public directory",
        f'<div class="grid">{cards}</div><p class="note">The public page uses a narrow projection of the team model. The API may return the whole object.</p>',
    )


@app.get("/api/v1/team")
def team_api():
    # VULNERABLE: serializes internal fields, including secrets and private notes.
    payload = []
    for member in TEAM:
        item = dict(member)
        item["private"] = {
            "personal_email": member["email"].replace("@teamspace.local", "@personal.local"),
            "security_note": "MFA reset pending" if member["id"] != 3 else "operations-vault",
        }
        if member["id"] == 3:
            item["private"]["vault_flag"] = lab.flag("flag")
            item["private"]["access_token_hint"] = "ops-console"
        payload.append(item)
    return jsonify({"team": payload, "count": len(payload)})


if __name__ == "__main__":
    lab.run()
