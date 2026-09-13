"""Match an existing Compose PostgreSQL volume to the local secret file."""

import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[1]
password = (root / ".secrets" / "db_password").read_text(encoding="utf-8").strip()
if not password:
    raise SystemExit(".secrets/db_password is empty")

# Send the password through stdin so it is not exposed as a process argument.
quoted_password = password.replace("'", "''")
subprocess.run(
    ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "queue", "-d", "queue"],
    input=f"ALTER ROLE queue WITH PASSWORD '{quoted_password}';\n",
    text=True,
    cwd=root,
    check=True,
)
