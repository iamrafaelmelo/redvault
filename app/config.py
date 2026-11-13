"""Central configuration for REDVAULT.

Everything is local-first. Override paths/ports with environment variables.
The platform binds to loopback only unless REDVAULT_HOST is explicitly changed.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("REDVAULT_DATA", BASE_DIR / "data")).resolve()
CONTENT_DIR = Path(os.environ.get("REDVAULT_CONTENT", BASE_DIR / "content")).resolve()
LABS_DIR = Path(os.environ.get("REDVAULT_LABS", BASE_DIR / "labs")).resolve()
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

HOST = os.environ.get("REDVAULT_HOST", "127.0.0.1")
PORT = int(os.environ.get("REDVAULT_PORT", "8000"))

DB_PATH = DATA_DIR / "redvault.db"
DB_URL = os.environ.get("REDVAULT_DB_URL", f"sqlite:///{DB_PATH}")

LAB_PORT_START = int(os.environ.get("REDVAULT_LAB_PORT_START", "42000"))
LAB_PORT_END = int(os.environ.get("REDVAULT_LAB_PORT_END", "42999"))
# Loopback by default. Set REDVAULT_LAB_BIND=0.0.0.0 to let another machine on
# the same LAN reach the labs (a "shared range" setup). Every lab is still an
# intentionally vulnerable app: only do this on a trusted, isolated network.
LAB_BIND = os.environ.get("REDVAULT_LAB_BIND", "127.0.0.1")
# Address advertised to the browser when the lab URL is built. Defaults to the
# bind address, but a LAN IP (e.g. 192.168.1.10) is clearer when bound to 0.0.0.0.
LAB_PUBLIC_HOST = os.environ.get("REDVAULT_LAB_PUBLIC_HOST", "")
MAX_ACTIVE_LABS = int(os.environ.get("REDVAULT_MAX_LABS", "5"))
LAB_IDLE_TIMEOUT = int(os.environ.get("REDVAULT_LAB_IDLE_TIMEOUT", str(45 * 60)))
# Hard ceiling on a single lab's lifetime, independent of activity. A forgotten
# lab does not stay exposed on a widened bind (REDVAULT_LAB_BIND) overnight.
LAB_MAX_LIFETIME = int(os.environ.get("REDVAULT_LAB_MAX_LIFETIME", str(2 * 60 * 60)))
LAB_START_TIMEOUT = int(os.environ.get("REDVAULT_LAB_START_TIMEOUT", "15"))
USE_BWRAP = os.environ.get("REDVAULT_USE_BWRAP", "1") not in {"0", "false", "no"}
BOT_ENABLED = os.environ.get("REDVAULT_BOT", "1") not in {"0", "false", "no"}
CHROMEDRIVER = os.environ.get("REDVAULT_CHROMEDRIVER", "/usr/bin/chromedriver")
BOT_TIMEOUT = int(os.environ.get("REDVAULT_BOT_TIMEOUT", "20"))

SESSION_COOKIE = "rv_session"
SESSION_TTL_HOURS = 72
# REDVAULT is single-operator and loopback-only: there is no login screen. The
# operator identity is created on first use with this name.
LOCAL_OPERATOR = os.environ.get("REDVAULT_OPERATOR", "operator")
CSRF_HEADER = "X-CSRF-Token"
INTERNAL_HEADER = "X-Redvault-Internal"

# Difficulty is ordered; used for sorting and recommendations.
DIFFICULTIES = ["beginner", "easy", "medium", "hard", "insane"]
DIFFICULTY_LABELS = {
    "beginner": "Iniciante",
    "easy": "Fácil",
    "medium": "Médio",
    "hard": "Difícil",
    "insane": "Insano",
}
DIFFICULTY_XP = {"beginner": 60, "easy": 110, "medium": 190, "hard": 320, "insane": 500}

LEVELS = [
    (0, "Iniciado", "Acesso concedido. O vault está aberto."),
    (600, "Operador I", "Você está construindo uma metodologia."),
    (1600, "Operador II", "A exploração independente está tomando forma."),
    (3200, "Especialista", "Você encadeia falhas e documenta evidências."),
    (5600, "Operador Sênior", "Alvos complexos cedem à pesquisa estruturada."),
    (9000, "Líder de Red Team", "A kill chain é sua."),
    (14000, "Fantasma", "O alvo nunca te viu."),
    (22000, "Lenda", "O vault lembra."),
]

CATEGORY_META = {
    "recon": ("Recon & Discovery", "Mapeie o desconhecido e encontre o que não deveria estar exposto.", "radar"),
    "auth": ("Autenticação", "Quebre identidade, sessões e fluxos de recuperação.", "key"),
    "access": ("Controle de Acesso", "Movimente-se horizontal e verticalmente entre objetos e papéis.", "lock"),
    "sqli": ("SQL Injection", "Converse com o banco de dados por trás da aplicação.", "database"),
    "xss": ("Cross-Site Scripting", "Execute no contexto do navegador da vítima.", "code"),
    "server": ("Ataques Server-Side", "Faça o servidor agir contra si mesmo.", "server"),
    "api": ("Segurança de API", "Explore contratos, objetos, versões e confiança.", "api"),
    "logic": ("Lógica de Negócio", "Abuse das regras, não do parser.", "flow"),
    "upload": ("Upload de Arquivos", "Transforme o manuseio de arquivos em execução ou vazamento.", "upload"),
    "client": ("Segurança Client-Side", "Ataque o DOM, a confiança do navegador e os dados do frontend.", "browser"),
    "advanced": ("Ataques Web Avançados", "Cache, race conditions e dessincronização na borda.", "bolt"),
    "chain": ("Encadeamento de Vulnerabilidades", "Um achado é apenas o começo.", "chain"),
}

SOURCE_TYPES = {
    "official": "Documentação oficial",
    "research": "Pesquisa de segurança",
    "advisory": "Aviso do fornecedor",
    "writeup": "Write-up da comunidade",
    "standard": "Padrão / framework",
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "labs").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "labs" / "logs").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "labs" / "state").mkdir(parents=True, exist_ok=True)


def load_secret() -> bytes:
    """Persist a single random master secret outside the database."""
    ensure_dirs()
    path = DATA_DIR / "secret.key"
    if path.exists():
        value = path.read_bytes().strip()
        if len(value) >= 32:
            return value
    value = secrets.token_hex(48).encode()
    path.write_bytes(value)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value


def level_for_xp(xp: int) -> tuple[int, str, int, int, str]:
    """Return (level, title, current_floor, next_floor, description)."""
    current = LEVELS[0]
    index = 0
    for i, entry in enumerate(LEVELS):
        if xp >= entry[0]:
            current = entry
            index = i
    next_floor = LEVELS[index + 1][0] if index + 1 < len(LEVELS) else current[0]
    return index + 1, current[1], current[0], next_floor, current[2]
