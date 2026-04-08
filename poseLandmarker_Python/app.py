from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from controller import analysis, health, jobs, results

app = FastAPI(title="Motion Analysis Backend")
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)

app.include_router(analysis.router)
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(results.router)
