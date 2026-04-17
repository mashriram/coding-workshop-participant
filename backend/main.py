import os
import sys
import json
import importlib.util
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Define the backend directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Fetch configuration from environment (set by Docker Compose in production)
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_NAME = os.getenv("POSTGRES_NAME", "postgres")
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASS = os.getenv("POSTGRES_PASS", "postgres123")
JWT_SECRET = os.getenv("JWT_SECRET", "acme-super-secret-jwt-key-2024")

app = FastAPI(title="ACME Performance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def normalize_slashes(request: Request, call_next):
    # If the path starts with //, collapse it to / to prevent 404s from stubborn client caches
    path = request.scope.get("path", "")
    if path.startswith("//"):
        request.scope["path"] = "/" + path.lstrip("/")
    return await call_next(request)

# Service Mapping
SERVICE_MAP = {
    "auth-service": "auth-service",
    "employees-service": "employees-service",
    "reviews-service": "reviews-service",
    "goals-service": "goals-service",
    "competencies-service": "competencies-service",
    "training-service": "training-service",
    "development-service": "development-service",
    "analytics-service": "analytics-service"
}

@app.on_event("startup")
async def startup_event():
    """Ensure all databases are initialized on startup."""
    print("🚀 Initializing service databases...")
    for svc in SERVICE_MAP:
        try:
            handler_module = load_service_module(svc)
            if hasattr(handler_module, "init_db"):
                print(f"  - Initializing {svc}...")
                handler_module.init_db()
        except Exception as e:
            print(f"  - ⚠️  Failed to init {svc}: {e}")

def load_service_module(service_name):
    """Dynamically loads service module with isolated dependencies."""
    for shared in ["jwt_utils", "postgres_service", "function"]:
        if shared in sys.modules:
            del sys.modules[shared]
    
    svc_dir = os.path.join(BACKEND_DIR, SERVICE_MAP[service_name])
    file_path = os.path.join(svc_dir, "function.py")
    module_name = f"mod_{service_name.replace('-', '_')}"
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    
    sys.path.insert(0, svc_dir)
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)

def load_service_handler(service_name):
    return load_service_module(service_name).handler

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.api_route("/api/{service_name}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.api_route("/api/{service_name}/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def unified_handler(service_name: str, request: Request, rest_of_path: str = ""):
    if service_name not in SERVICE_MAP:
        return Response(content=json.dumps({"error": f"Service {service_name} not found"}), status_code=404)

    try:
        handler = load_service_handler(service_name)
    except Exception as e:
        return Response(content=json.dumps({"error": f"Failed to load service: {str(e)}"}), status_code=500)
    
    body = await request.body()
    try:
        body_str = body.decode('utf-8')
    except:
        body_str = ""

    relative_path = f"/{rest_of_path}"
    event_headers = {k: v for k, v in request.headers.items()}
    # Ensure Authorization is present in expected case if it exists in lower case
    if "authorization" in event_headers and "Authorization" not in event_headers:
        event_headers["Authorization"] = event_headers["authorization"]

    # Construct the Lambda Event Object
    event = {
        "httpMethod": request.method,
        "path": relative_path,
        "headers": event_headers,
        "queryStringParameters": dict(request.query_params) if request.query_params else None,
        "body": body_str,
        "isBase64Encoded": False,
        "requestContext": {
            "http": {
                "method": request.method,
                "path": relative_path
            }
        }
    }

    try:
        result = handler(event, None)
        status = result.get("statusCode", 200)
        resp_payload = result.get("body", "")
        headers = result.get("headers", {})
        
        # Consistent string handling for bodies
        if not isinstance(resp_payload, str):
            resp_payload = json.dumps(resp_payload)
            
        # Ensure correct media type to prevent explicit string casting overrides
        media_type = headers.get("Content-Type", "application/json") if headers else "application/json"
        
        return Response(
            content=resp_payload,
            status_code=status,
            headers=headers,
            media_type=media_type
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(content=json.dumps({"error": str(e)}), status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
