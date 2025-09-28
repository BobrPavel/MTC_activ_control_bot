from .base import admin_router as base_router
from .cards import admin_router as cards_router
from .players import admin_router as players_router
from .reports import admin_router as reports_router
from .controls import admin_router as controls_router
from .fsm import admin_router as fsm_router

admin_routers = [
    base_router,
    cards_router,
    players_router,
    reports_router,
    controls_router,
    fsm_router,
]
