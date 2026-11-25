"""Configura uma copia local do GIRO sem expor a senha root no comando."""

from __future__ import annotations

import configparser
import getpass
import gzip
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import mysql.connector


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "mysql" / "runtime"
BACKUP = ROOT / "entrega" / "GIRO_mysql_A3.sql.gz"
ROOT_OPTIONS = RUNTIME / "root.cnf"
APP_OPTIONS = RUNTIME / "app.cnf"
DEMO_OPTIONS = RUNTIME / "demo.cnf"


def mysql_client() -> Path:
    candidates = [Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe")]
    found = shutil.which("mysql")
    if found:
        candidates.append(Path(found))
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("mysql.exe nao encontrado. Instale MySQL Server 8.4 pelo winget.")


def saved_root_password() -> str | None:
    if not ROOT_OPTIONS.is_file():
        return None
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ROOT_OPTIONS, encoding="utf-8")
    return parser.get("client", "password", fallback=None)


def connect_root():
    password = saved_root_password()
    if password is None:
        password = getpass.getpass("Senha root do MySQL local: ")
    try:
        connection = mysql.connector.connect(user="root", password=password,
                                             host="127.0.0.1", port=3306,
                                             connection_timeout=8)
    except mysql.connector.Error as error:
        raise RuntimeError(
            "Nao foi possivel acessar o MySQL na porta 3306. Confira se o MySQL "
            "Configurator concluiu a instalacao, se o servico esta iniciado "
            "e se a senha root esta correta."
        ) from error
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if not ROOT_OPTIONS.exists():
        ROOT_OPTIONS.write_text(
            f"[client]\nuser=root\npassword={password}\nhost=127.0.0.1\nport=3306\n",
            encoding="utf-8",
        )
    return connection


def restore_database(connection, client: Path) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables "
                       "WHERE TABLE_SCHEMA='giro_a3' AND TABLE_TYPE='BASE TABLE'")
        table_count = cursor.fetchone()[0]
        if table_count >= 7:
            print("Banco giro_a3 ja existe; dados preservados.")
            return
        if table_count:
            raise RuntimeError("Banco giro_a3 incompleto. Nao vou sobrescrever tabelas existentes.")
        cursor.execute("CREATE DATABASE IF NOT EXISTS giro_a3 CHARACTER SET utf8mb4")
    connection.commit()
    print("Restaurando a amostra de 500 mil clientes e 750 mil vendas. Aguarde...")
    with tempfile.TemporaryFile() as error_stream:
        process = subprocess.Popen(
            [str(client), f"--defaults-extra-file={ROOT_OPTIONS}",
             "--default-character-set=utf8mb4", "--database=giro_a3"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=error_stream,
        )
        try:
            with gzip.open(BACKUP, "rb") as source:
                shutil.copyfileobj(source, process.stdin, length=1024 * 1024)
            process.stdin.close()
            code = process.wait()
        except Exception:
            process.kill()
            process.wait()
            raise
        if code:
            error_stream.seek(0)
            message = error_stream.read(2000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Falha ao restaurar o dump MySQL: {message}")
    print("Backup restaurado.")


def configure_demo(connection) -> None:
    if DEMO_OPTIONS.exists():
        return
    password = secrets.token_urlsafe(32)
    with connection.cursor() as cursor:
        cursor.execute("CREATE USER IF NOT EXISTS 'giro_demo'@'127.0.0.1' IDENTIFIED BY %s", (password,))
        cursor.execute("ALTER USER 'giro_demo'@'127.0.0.1' IDENTIFIED BY %s", (password,))
        cursor.execute("GRANT SELECT, SHOW VIEW ON giro_a3.* TO 'giro_demo'@'127.0.0.1'")
    connection.commit()
    DEMO_OPTIONS.write_text(
        f"[client]\nuser=giro_demo\npassword={password}\nhost=127.0.0.1\nport=3306\n",
        encoding="utf-8",
    )
    (ROOT / "mysql" / "CONEXAO_LOCAL.txt").write_text(
        "Conexao local do MySQL Workbench para GIRO\n"
        "Host: 127.0.0.1\nPorta: 3306\nUsuario: giro_demo\n"
        f"Senha: {password}\nEsquema: giro_a3\n",
        encoding="utf-8",
    )
    print("Conta de leitura para Workbench criada; dados em mysql/CONEXAO_LOCAL.txt.")


def verify(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM giro_a3.customer")
        customers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM giro_a3.sale")
        sales = cursor.fetchone()[0]
    if customers < 500_000 or sales < 750_000:
        raise RuntimeError(f"Amostra incompleta: {customers} clientes, {sales} vendas.")
    print(f"Banco pronto: {customers} clientes, {sales} vendas.")


def main() -> None:
    if not BACKUP.is_file():
        raise RuntimeError(f"Backup ausente: {BACKUP}")
    client = mysql_client()
    if "--check" in sys.argv:
        print(f"MySQL client: {client}")
        print(f"Backup: {BACKUP.stat().st_size // 1024 // 1024} MB")
        print(f"App configurado: {APP_OPTIONS.is_file()}")
        return
    with connect_root() as connection:
        restore_database(connection, client)
        verify(connection)
        configure_demo(connection)
    subprocess.run([sys.executable, "-m", "scripts.configurar_app_mysql"], cwd=ROOT, check=True)
    print("Pronto. Inicie o painel com INICIAR_GIRO.cmd.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, mysql.connector.Error, OSError, subprocess.CalledProcessError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        raise SystemExit(1)
