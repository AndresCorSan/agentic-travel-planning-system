"""Shared FastAPI dependencies (access to the startup-built graph)."""
from fastapi import Request


def get_graph(request: Request):
    return request.app.state.graph
