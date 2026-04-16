import os
import sys
import json
import importlib.util
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Add absolute path to backend
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure environment for all handlers
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_NAME"] = "postgres"
os.environ["POSTGRES_USER"] = "postgres"
os.environ["POSTGRES_PASS"] = "postgres123"
os.environ["IS_LOCAL"] = "true"
os.environ["JWT_SECRET"] = "acme-super-secret-jwt-key-2024"

# Critical: Handlers often expect specific case for headers (e.g. 'Authorization')
# We will provide a helper to wrap headers in a case-insensitive way if needed,
# but passing original headers is safer.

app = FastAPI(redirect_slashes=False) # Disable automatic slashes to prevent 307s

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Map prefix to service folder
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

# we store them BY service_name to ensure isolation.
service_modules = {}

def load_service_handler(service_name):
    """Loads a service-specific handler using a unique module name space."""
    # To truly isolate, we clear shared module names from sys.modules
    # so they are re-imported from the service-specific directory.
    for shared in ["jwt_utils", "postgres_service", "jwt_utils", "postgres_service", "function"]:
        if shared in sys.modules:
            del sys.modules[shared]
    
    svc_dir = os.path.join(BACKEND_DIR, SERVICE_MAP[service_name])
    file_path = os.path.join(svc_dir, "function.py")
    
    # We load it every time for now to ensure absolute isolation of dependencies
    # like postgres_service.py which exists in every folder.
    module_name = f"run_service_{service_name.replace('-', '_')}"
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    
    sys.path.insert(0, svc_dir)
    try:
        spec.loader.exec_module(module)
        return module.handler
    finally:
        sys.path.pop(0)

@app.api_route("/api/{service_name}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.api_route("/api/{service_name}/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_to_handler(service_name: str, request: Request, rest_of_path: str = ""):
    if service_name not in SERVICE_MAP:
        return Response(content=json.dumps({"error": f"Unknown service: {service_name}"}), status_code=404)

    try:
        handler = load_service_handler(service_name)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(content=json.dumps({"error": f"Failed to load service {service_name}: {str(e)}"}), status_code=500)
    
    body = await request.body()
    try:
        body_str = body.decode('utf-8')
    except:
        body_str = ""

    relative_path = f"/{rest_of_path}"
    
    # CRITICAL: Preserve header case! Handlers use .get("Authorization")
    event_headers = {k: v for k, v in request.headers.items()}
    # Also inject capitalized versions just in case
    if "authorization" in event_headers and "Authorization" not in event_headers:
        event_headers["Authorization"] = event_headers["authorization"]

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

    print(f"[{service_name}] Routing {request.method} {relative_path}")
    
    try:
        result = handler(event, None)
        
        status = result.get("statusCode", 200)
        resp_body = result.get("body", "")
        headers = result.get("headers", {})
        
        if not isinstance(resp_body, str):
            resp_body = json.dumps(resp_body)
            
        return Response(
            content=resp_body,
            status_code=status,
            headers=headers
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(content=json.dumps({"error": str(e)}), status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
