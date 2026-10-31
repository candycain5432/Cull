# The local web server behind the review screen, it can only be reached from this computer
import secrets
import socket
import threading
import webbrowser
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from cull.analyze import UNREADABLE
from cull.previews import BROWSER_READY, render

HOST = "127.0.0.1"
KEEP_FOR = {"Cache-Control": "private, max-age=86400"} # Every run has its own URLs, so a photo never goes stale


class Change(BaseModel):
    id: int
    decision: Literal["pick", "reject"] | None


class Changes(BaseModel):
    changes: list[Change]


def create_app(shoot, decisions, config):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # Stops a website from pointing its own domain at this computer to read the photos
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[HOST, "localhost"])
    run = secrets.token_hex(4)

    def find(photo_id):
        if not 0 <= photo_id < len(shoot.names):
            raise HTTPException(404, "No such photo")
        return shoot.names[photo_id]

    def picture(file, edge=None):
        try:
            return Response(render(file, config.files.raw_extensions, edge), media_type="image/jpeg", headers=KEEP_FOR)
        except UNREADABLE as e: # Moved or changed since the run started
            raise HTTPException(404, str(e))

    @app.get("/api/shoot")
    def read_shoot():
        saved = decisions.saved
        return {"name": shoot.folder.name, "run": run, "autoAdvance": config.review.auto_advance, "sections": shoot.sections,
                "decisions": {number: saved[name] for number, name in enumerate(shoot.names) if name in saved}}

    # Browsers won't let another website send JSON here, but they would let it send a plain form
    @app.post("/api/decisions")
    def save_decisions(body: Changes, request: Request):
        if request.headers.get("content-type") != "application/json":
            raise HTTPException(415, "Decisions have to be sent as JSON")
        changes = [(find(change.id), change.decision) for change in body.changes]
        try:
            decisions.apply(changes)
        except OSError as e:
            raise HTTPException(500, f"Couldn't save {decisions.path}: {e.strerror}")
        return {"saved": len(changes)}

    @app.get("/photos/{photo_id}/thumb")
    def thumbnail(photo_id: int):
        return picture(shoot.folder / find(photo_id), config.review.thumbnail)

    @app.get("/photos/{photo_id}/full")
    def full_size(photo_id: int):
        file = shoot.folder / find(photo_id)
        if file.suffix.lower() not in BROWSER_READY:
            return picture(file)
        if not file.is_file():
            raise HTTPException(404, "That photo has moved")
        return FileResponse(file, headers=KEEP_FOR)

    app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True)) # Last, it answers every other path
    return app


# Taking the port before the server starts gives a clear error, and the browser can't arrive too early
def listen(port):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((HOST, port))
        sock.listen()
    except OSError:
        sock.close()
        raise
    return sock, f"http://{HOST}:{sock.getsockname()[1]}"


# Runs until Ctrl+C
def serve(app, sock, url, open_browser):
    if open_browser: # A text browser would hold the terminal, so this gets its own thread
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()

    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False, timeout_graceful_shutdown=1))
    try:
        server.run(sockets=[sock])
    except KeyboardInterrupt: # Finishing a review is normal, Uvicorn passes the Ctrl+C on once it has stopped
        pass
