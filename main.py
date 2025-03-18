from fastapi import FastAPI
from app.controllers.collection_controller import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Collection API",
    description="API for collecting housing data", 
    version="1.0.0")

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
