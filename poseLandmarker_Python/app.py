from fastapi import FastAPI

from controller import health, jobs, results

app = FastAPI(title="Motion Analysis Backend")

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(results.router)
