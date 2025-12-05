# GitHub Repositories Viewer

Simple full stack application using **FastAPI**, **SQLAlchemy**, and **PostgreSQL** to fetch public repositories from a GitHub user, save/update them in the database, and display them in an HTML/CSS/JS frontend.

## Stack

- Backend: Python 3.13 + FastAPI
- ORM: SQLAlchemy
- Database: PostgreSQL
- Frontend: HTML + CSS + JS
- Background tasks: APScheduler

## How to run locally

### 1. Clone the project and enter the folder

```
cd github_repos_app
```

### 2. Create a virtual environment

```
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Start PostgreSQL(Docker) and Create Database

```
docker run --name github_repos_db -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=github_repos-p 5432:5432 -d postgres:16

CREATE DATABASE github_repos
```

### 5. Configure DATABASE_URL or Edit database.py

```
# Windows (PowerShell):
$env:DATABASE_URL="postgresql+psycopg2://postgres:password@localhost:5432/github_repos"
```

### 6. Run the application

```
uvicorn main:app --reload
```