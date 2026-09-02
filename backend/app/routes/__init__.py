from .call_routes import router as call_router
from .knowledge_routes import router as knowledge_router
from .logs_routes import router as logs_router
from .ticket_routes import router as ticket_router
from .telephony_routes import router as telephony_router

__all__ = ["call_router", "knowledge_router", "logs_router", "ticket_router", "telephony_router"]
