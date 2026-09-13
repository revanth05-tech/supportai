from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.rag.router import router


def test_rag_chat_route_is_registered():
    routes = [
        (route.path, route.methods)
        for route in router.routes
        if isinstance(route, APIRoute)
    ]

    assert ("/api/rag/chat", {"POST"}) in routes