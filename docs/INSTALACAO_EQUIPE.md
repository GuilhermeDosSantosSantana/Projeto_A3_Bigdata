# Instalar o GIRO em outro Windows

1. Baixe somente [`INSTALAR_GIRO.bat`](https://raw.githubusercontent.com/GuilhermeDosSantosSantana/Projeto_A3_Bigdata/main/INSTALAR_GIRO.bat) e salve em uma pasta sua, por exemplo `Documentos\GIRO`.
2. Execute o arquivo com dois cliques. Ele baixa esta copia do projeto do GitHub quando ainda nao estiver na mesma pasta. Em seguida usa o `winget` para instalar Python 3.13, Visual C++ Runtime, MySQL Server 8.4 e MySQL Workbench, e cria `.venv` com as bibliotecas de `requirements.txt`.
3. Se o instalador do MySQL abrir o **MySQL Configurator**, conclua a configuracao local na porta **3306** e guarde a senha `root`. Execute o `.bat` novamente se ele tiver parado para aguardar a configuracao.
4. Quando o terminal pedir a senha `root`, digite-a ali. Ela nao aparece na tela. O script cria o esquema `giro_a3` a partir de `entrega/GIRO_mysql_A3.sql.gz`, verifica 500 mil clientes e 750 mil vendas e cria contas locais restritas para o painel e para consulta no Workbench.
5. O painel abre em <http://127.0.0.1:3000>. Para as proximas vezes, use `INICIAR_GIRO.cmd` na pasta baixada. Para abrir o Workbench, use `INICIAR_MYSQL_GIRO.cmd` e crie uma conexao local com os dados em `mysql/CONEXAO_LOCAL.txt`.

O backup compactado tem aproximadamente 21 MB e o SQL restaurado tem aproximadamente 103 MB. Reserve espaco adicional para a instalacao do MySQL, seus indices e o ambiente Python. O script preserva um banco `giro_a3` ja preenchido: ao ser executado novamente, nao apaga os dados.

Os arquivos de senha ficam em `mysql/runtime/` e `mysql/CONEXAO_LOCAL.txt`, ignorados pelo Git. Nao envie esses arquivos para outras pessoas. O Redis e opcional; sem ele, o GIRO usa um cache temporario em memoria.

Para conferir as dependencias sem baixar ou instalar nada, rode `INSTALAR_GIRO.bat --check` em um terminal aberto na pasta do projeto.

Se o `winget` nao estiver presente, instale o **App Installer** da Microsoft e rode o mesmo arquivo novamente. Os pacotes sao obtidos do repositorio padrao `winget`. A [documentacao da Microsoft](https://learn.microsoft.com/windows/package-manager/winget/install) descreve o uso de IDs exatos; a [documentacao da Oracle](https://dev.mysql.com/doc/refman/8.4/en/windows-installation.html) explica por que o servidor precisa do MySQL Configurator antes de iniciar.
