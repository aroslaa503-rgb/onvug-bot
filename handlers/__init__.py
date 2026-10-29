from .start import router as start_router
from .profile import router as profile_router
from .ai_chat import router as ai_router
from .admin import router as admin_router

all_routers = [
    start_router,
    profile_router,
    ai_router,
    admin_router,
]
