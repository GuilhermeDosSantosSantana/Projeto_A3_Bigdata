"""Build a credential-free pitch package with app, SQL and evidence."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "entrega" / "GIRO_A3_pacote_pitch.zip"
FILES = [
    "README.md", "requirements.txt", "INICIAR_GIRO.cmd", "INICIAR_GIRO.ps1",
    "INICIAR_MYSQL_GIRO.cmd", "INICIAR_MYSQL_GIRO.ps1",
    "giro/__init__.py", "giro/cache.py", "giro/mysql_db.py", "giro/server.py",
    "mysql/my.ini", "mysql/01_schema.sql", "mysql/02_seed.sql",
    "mysql/04_trigger.sql", "mysql/05_enable_app_writes.sql",
    "scripts/configurar_app_mysql.py", "scripts/testar_fluxo_web.py", "scripts/testar_front.py", "scripts/validar_api_leitura.py", "scripts/relatorio.py",
    "scripts/validar_mysql.py", "scripts/gerar_amostra_mysql.py",
    "entrega/GIRO_mysql_A3.sql.gz", "output/pdf/GIRO_relatorio_A3.pdf",
]
for folder in ("web", "mysql/consultas", "docs", "evidencias"):
    FILES += [p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*") if p.is_file()]

TARGET.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(TARGET, "w") as archive:
    for name in sorted(set(FILES)):
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        archive.write(path, name, ZIP_STORED if name.endswith(".gz") else ZIP_DEFLATED)
print(f"Pacote atualizado: {TARGET} ({TARGET.stat().st_size // 1024 // 1024} MB)")
