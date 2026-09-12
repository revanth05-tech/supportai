"""Reserved middleware registration seam for later auth and tenant resolution."""

from fastapi import FastAPI


def register_middleware(_: FastAPI) -> None:
    """Keep middleware wiring centralized without adding behavior in Step 1."""
