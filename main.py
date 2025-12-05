from __future__ import annotations

from datetime import datetime
from typing import List

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from models import Repository, User
from schemas import RepositoryBase, UserSyncResponse

app = FastAPI(title="GitHub Repositories Viewer")


Base.metadata.create_all(bind=engine)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

GITHUB_API_URL = "https://api.github.com/users/{username}/repos"

scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def startup_event() -> None:
    """Starts the periodic update scheduler."""
    scheduler.add_job(
        refresh_all_users,
        "interval",
        minutes=30,
        id="refresh_users",
        replace_existing=True,
    )
    scheduler.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Shuts down the scheduler cleanly."""
    scheduler.shutdown(wait=False)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Renders the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


async def fetch_github_repos(username: str) -> List[dict]:
    """
    Queries the public GitHub API and returns
    up to 5 repositories.
    """
    url = GITHUB_API_URL.format(username=username)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Error querying GitHub: {response.status_code}",
        )

    data = response.json()
    if not isinstance(data, list):
        raise HTTPException(
            status_code=502,
            detail="Unexpected response from GitHub API.",
        )

    
    return data[:5]


def upsert_user_and_repos(
    db: Session,
    username: str,
    repos_data: List[dict],
) -> UserSyncResponse:
    """
    Upsert user + repositories from GitHub data.

    - Creates user if not exists.
    - Updates existing repositories based on github_id.
    - Creates new repositories if necessary.
    - Removes repositories that fell out of the top 5 (optional, but
      keeps the database consistent with what is displayed).
    """
    user = db.query(User).filter(User.username == username).first()
    is_new = False

    if user is None:
        user = User(username=username)
        db.add(user)
        db.flush()  
        is_new = True

    github_repo_ids: List[int] = []

    for repo in repos_data:
        github_id = repo.get("id")
        if github_id is None:
            
            continue

        github_repo_ids.append(github_id)

        db_repo = (
            db.query(Repository)
            .filter(
                Repository.user_id == user.id,
                Repository.github_id == github_id,
            )
            .first()
        )

        if db_repo is None:
            db_repo = Repository(
                user_id=user.id,
                github_id=github_id,
            )
            db.add(db_repo)

        db_repo.name = repo.get("name")
        db_repo.html_url = repo.get("html_url")
        db_repo.description = repo.get("description")
        db_repo.language = repo.get("language")

    
    (
        db.query(Repository)
        .filter(Repository.user_id == user.id)
        .filter(~Repository.github_id.in_(github_repo_ids))
        .delete(synchronize_session=False)
    )

    user.last_synced_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    repos = (
        db.query(Repository)
        .filter(Repository.user_id == user.id)
        .order_by(Repository.name.asc())
        .all()
    )

    return UserSyncResponse(
        username=user.username,
        status="new" if is_new else "updated",
        is_new=is_new,
        repositories=[RepositoryBase.from_orm(r) for r in repos],
    )


@app.post("/api/github/{username}", response_model=UserSyncResponse)
async def sync_github_user(
    username: str,
    db: Session = Depends(get_db),
) -> UserSyncResponse:
    """
    Main endpoint:
    - Receives username
    - Queries GitHub
    - Performs upsert in database
    - Returns data and status (new/updated)
    """
    repos_data = await fetch_github_repos(username)
    response = upsert_user_and_repos(db, username, repos_data)
    return response


async def refresh_user(db: Session, username: str) -> None:
    """Updates data for a specific user (used by the scheduled task)."""
    try:
        repos_data = await fetch_github_repos(username)
        upsert_user_and_repos(db, username, repos_data)
    except HTTPException as exc:
        
        print(f"Error updating user {username}: {exc.detail}")


async def refresh_all_users() -> None:
    """
    Job scheduled by APScheduler:
    - Iterates through all users in the database
    - Re-queries GitHub
    - Updates the data
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        usernames = [u.username for u in users]
    finally:
        db.close()

    
    for username in usernames:
        db = SessionLocal()
        try:
            await refresh_user(db, username)
        finally:
            db.close()