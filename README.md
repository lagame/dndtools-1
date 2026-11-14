dndtools
==========

An open source Django-based wiki-like web application for DnD.

Status
------
This github repository is currently a clone of a private repository. It contains ONLY source codes of the application, not its data.

The database is not uploaded to this repository. If you need a copy to run
the project locally, open an issue in this repository and request it. Do not
upload the database publicly.

Also, this readme file is just an early preview to be updated as soon as someone have the time.

If you find anything wrong, just start an issue.

Local setup (modernized)
------------------------
The original project targeted Python 2 and an old Django release. The local
modernized setup runs on Python 3 with Django 5 and uses a pre-populated
SQLite database when `dnd.sqlite` is available.

On Windows PowerShell, from the repository root:

```sh
# Clone the repository
git clone https://github.com/dndtools/dndtools.git
cd dndtools/

# Create and use a Python 3 virtual environment
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-modern.txt

# Put the SQLite data file at the repository root as dnd.sqlite.
# Then apply only the framework migrations; the legacy content tables already
# exist in the supplied database.
.\.venv\Scripts\python.exe dndtools\manage.py migrate --noinput

# Run the local server
.\.venv\Scripts\python.exe dndtools\manage.py runserver 127.0.0.1:8765
```

The site is then available at <http://127.0.0.1:8765/>.

The file `dndtools/dndproject/local.py` is intentionally local-only and is
ignored by Git. Copy `dndtools/dndproject/local.py.sample` to that path when
setting up a fresh checkout.

Configuração local em português (Windows)
------------------------------------------
Este trecho reproduz o ambiente usado neste fork. Execute os comandos no
PowerShell, a partir da pasta do projeto.

```powershell
# Baixar o fork corrigido
git clone https://github.com/lagame/dndtools-1.git
cd dndtools-1

# Criar o ambiente virtual Python 3
py -3 -m venv .venv

# Instalar as dependências modernas
.\.venv\Scripts\python.exe -m pip install -r requirements-modern.txt

# Criar a configuração local ignorada pelo Git
Copy-Item dndtools\dndproject\local.py.sample dndtools\dndproject\local.py

# Colocar o arquivo dnd.sqlite na raiz do projeto.
# Para solicitar uma cópia, abra uma Issue neste repositório.
# O envio do banco será combinado por canal privado; não o publique na Issue.

# Aplicar as migrações do Django
.\.venv\Scripts\python.exe dndtools\manage.py migrate --noinput

# Iniciar o site
.\.venv\Scripts\python.exe dndtools\manage.py runserver 127.0.0.1:8765
```

Depois, abra <http://127.0.0.1:8765/> no navegador. Não faça commit do
`dnd.sqlite`: o arquivo contém os dados do site e fica fora do repositório.

Legacy installation
-------------------
The original Python 2/Django installation instructions are retained in the
repository history. They are not the recommended path for a new local setup.
