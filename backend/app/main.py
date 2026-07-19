from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router


# Load private environment variables.
load_dotenv()


app = FastAPI(
    title="DataPulse AI API",
    description=(
        "Backend API for the DataPulse AI autonomous "
        "data incident intelligence and response agent."
    ),
    version="1.0.0",
)


# Allow the local Next.js frontend to communicate
# with the FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    router
)


@app.get("/")
def root() -> dict:
    return {
        "name": "DataPulse AI",
        "description": (
            "Autonomous Data Incident Intelligence "
            "& Response Agent"
        ),
        "api_docs": "/docs",
        "health": "/api/health",
        "system_status": "/api/system/status",
    }