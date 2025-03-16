from fastapi import FastAPI
from controllers.collection_controller import router

app = FastAPI(
    title="Collection API",
    description="API for collecting housing data", 
    version="1.0.0")
app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
