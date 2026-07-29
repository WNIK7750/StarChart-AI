from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import FRONTEND_DIR, PUBLIC_BASE_PATH


router = APIRouter(include_in_schema=False)
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def canonical_location(
    path: str,
    query_items: Iterable[tuple[str, str]] = (),
) -> str:
    location = f"{PUBLIC_BASE_PATH}{path}" if PUBLIC_BASE_PATH else path
    query = urlencode(list(query_items), doseq=True)
    return f"{location}?{query}" if query else location


def page(filename: str) -> FileResponse:
    return FileResponse(FRONTEND_DIR / filename, media_type="text/html")


def permanent(
    path: str,
    query_items: Iterable[tuple[str, str]] = (),
) -> RedirectResponse:
    return RedirectResponse(canonical_location(path, query_items), status_code=308)


def request_query(request: Request, *, exclude: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    return [
        (name, value)
        for name, value in request.query_params.multi_items()
        if name not in exclude
    ]


@router.api_route("/", methods=["GET", "HEAD"])
def home_page() -> FileResponse:
    return page("index.html")


@router.api_route("/assistant", methods=["GET", "HEAD"])
def assistant_page() -> FileResponse:
    return page("assistant.html")


@router.api_route("/learn", methods=["GET", "HEAD"])
def learn_page() -> FileResponse:
    return page("learn.html")


@router.api_route("/tools", methods=["GET", "HEAD"])
def tools_page() -> FileResponse:
    return page("tools.html")


@router.api_route("/settings", methods=["GET", "HEAD"])
def settings_page() -> FileResponse:
    return page("settings.html")


@router.api_route("/learn/{slug}", methods=["GET", "HEAD"])
def learn_node_page(slug: str) -> FileResponse:
    if not SLUG_PATTERN.fullmatch(slug):
        raise HTTPException(status_code=404, detail="Page not found")
    return page("learn-node.html")


@router.api_route("/assistant/", methods=["GET", "HEAD"])
def canonicalize_assistant(request: Request) -> RedirectResponse:
    return permanent("/assistant", request_query(request))


@router.api_route("/learn/", methods=["GET", "HEAD"])
def canonicalize_learn(request: Request) -> RedirectResponse:
    return permanent("/learn", request_query(request))


@router.api_route("/tools/", methods=["GET", "HEAD"])
def canonicalize_tools(request: Request) -> RedirectResponse:
    return permanent("/tools", request_query(request))


@router.api_route("/settings/", methods=["GET", "HEAD"])
def canonicalize_settings(request: Request) -> RedirectResponse:
    return permanent("/settings", request_query(request))


@router.api_route("/learn/{slug}/", methods=["GET", "HEAD"])
def canonicalize_learn_node(slug: str, request: Request) -> RedirectResponse:
    if not SLUG_PATTERN.fullmatch(slug):
        raise HTTPException(status_code=404, detail="Page not found")
    return permanent(f"/learn/{slug}", request_query(request))


@router.api_route("/index.html", methods=["GET", "HEAD"])
def legacy_index(request: Request) -> RedirectResponse:
    return permanent("/", request_query(request))


@router.api_route("/assistant.html", methods=["GET", "HEAD"])
def legacy_assistant(request: Request) -> RedirectResponse:
    return permanent("/assistant", request_query(request))


@router.api_route("/learn.html", methods=["GET", "HEAD"])
def legacy_learn(request: Request) -> RedirectResponse:
    return permanent("/learn", request_query(request))


@router.api_route("/tools.html", methods=["GET", "HEAD"])
def legacy_tools(request: Request) -> RedirectResponse:
    return permanent("/tools", request_query(request))


@router.api_route("/settings.html", methods=["GET", "HEAD"])
def legacy_settings(request: Request) -> RedirectResponse:
    return permanent("/settings", request_query(request))


@router.api_route("/learn-node.html", methods=["GET", "HEAD"])
def legacy_learn_node(request: Request) -> RedirectResponse:
    slug = request.query_params.get("slug", "")
    query = request_query(request, exclude=frozenset({"slug"}))
    if not SLUG_PATTERN.fullmatch(slug):
        return permanent("/learn", query)
    return permanent(f"/learn/{slug}", query)
