import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.apps.cashin.api import router as cashin_router
from src.apps.cashin.exception_handlers import (
    EXCEPTION_HANDLERS as CASHIN_EXCEPTION_HANDLERS,
)
from src.apps.customerorder.api import router as customerorder_router
from src.apps.customerorder.exception_handlers import (
    EXCEPTION_HANDLERS as CUSTOMERORDER_EXCEPTION_HANDLERS,
)
from src.apps.hooks.api import router as hooks_router
from src.apps.hooks.exception_handlers import (
    EXCEPTION_HANDLERS as HOOKS_EXCEPTION_HANDLERS,
)
from src.apps.ms_auth.api import router as ms_auth_router
from src.apps.paymentin.api import router as paymentin_router
from src.apps.paymentin.exception_handlers import (
    EXCEPTION_HANDLERS as PAYMENTIN_EXCEPTION_HANDLERS,
)
from src.apps.vendor_api.api import router as vendor_api_router
from src.core.database import init_db
from src.core.logging_config import setup_logging

Path("logs").mkdir(exist_ok=True)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="МС: Автоматическая привязка платежей",
    lifespan=lifespan,
)

for exc_class, handler in HOOKS_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)

for exc_class, handler in CUSTOMERORDER_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)

for exc_class, handler in CASHIN_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)

for exc_class, handler in PAYMENTIN_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)

app.mount("/static", StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {
        "request": request,
        "page_title": "Автоматическая привязка платежей",
    }
    return templates.TemplateResponse("index.html", context)


app.include_router(ms_auth_router, prefix="/api/auth/ms", tags=["ms_auth"])
app.include_router(vendor_api_router, prefix="/api", tags=["vendor_api"])
app.include_router(hooks_router, prefix="/api/hooks", tags=["hooks"])
app.include_router(customerorder_router, prefix="/api/customerorder", tags=["customerorder"])
app.include_router(cashin_router, prefix="/api/cashin", tags=["cashin"])
app.include_router(paymentin_router, prefix="/api/paymentin", tags=["paymentin"])