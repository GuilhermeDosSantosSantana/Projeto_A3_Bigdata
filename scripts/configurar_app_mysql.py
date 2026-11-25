"""Create a local least-privilege account for the GIRO web application."""

from __future__ import annotations

import configparser
import secrets
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "mysql" / "runtime"


def config(path: Path) -> dict:
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    section = parser["client"]
    return {"user": section["user"], "password": section["password"],
            "host": section.get("host", "127.0.0.1"),
            "port": section.getint("port", 3306)}


def main() -> None:
    target = RUNTIME / "app.cnf"
    if target.exists():
        print("Conta do aplicativo ja configurada.")
        return
    password = secrets.token_urlsafe(32)
    with mysql.connector.connect(**config(RUNTIME / "root.cnf")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE USER IF NOT EXISTS 'giro_app'@'127.0.0.1' IDENTIFIED BY %s", (password,))
            cursor.execute("ALTER USER 'giro_app'@'127.0.0.1' IDENTIFIED BY %s", (password,))
            cursor.execute("GRANT SELECT, INSERT, UPDATE, SHOW VIEW ON giro_a3.* TO 'giro_app'@'127.0.0.1'")
        connection.commit()
    target.write_text("[client]\nuser=giro_app\npassword=" + password +
                      "\nhost=127.0.0.1\nport=3306\n", encoding="utf-8")
    print("Conta local do aplicativo configurada.")


if __name__ == "__main__":
    main()
