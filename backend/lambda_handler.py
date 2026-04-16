import os
from mangum import Mangum
from main import app, SERVICE_MAP, load_service_module

# Configure Mangum handler
# API Gateway Proxy events are passed directly to FastAPI
handler = Mangum(app, lifespan="off")

# Pre-initialize databases during Lambda cold start
def cold_start_init():
    print("LAMBDA COLD START: Initializing databases for unified backend...")
    for svc in SERVICE_MAP:
        try:
            handler_module = load_service_module(svc)
            if hasattr(handler_module, "init_db"):
                handler_module.init_db()
        except Exception as e:
            print(f"Warning: Failed to init DB for {svc} during cold start: {e}")

try:
    cold_start_init()
except Exception as e:
    print(f"LAMBDA COLD START ERROR: {e}")
