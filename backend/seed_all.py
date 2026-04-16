import os
import sys
import importlib

# Set environment variables for local DB if not already set
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_NAME", "postgres")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASS", "postgres123")
os.environ.setdefault("IS_LOCAL", "true")

SERVICES = [
    "auth-service",
    "employees-service",
    "reviews-service",
    "goals-service",
    "competencies-service",
    "training-service",
    "development-service"
]

def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, backend_dir)

    for service in SERVICES:
        print(f"Initializing {service}...")
        service_path = os.path.join(backend_dir, service)
        sys.path.insert(0, service_path)
        
        try:
            # Import the module dynamically
            module = importlib.import_module("function")
            if hasattr(module, "init_db"):
                module.init_db()
                print(f"  ✓ {service} DB initialized.")
            else:
                print(f"  ! {service} has no init_db.")
        except Exception as e:
            print(f"  ✗ Failed to initialize {service}: {e}")
        finally:
            # Remove from path to avoid conflicts for next service
            sys.path.remove(service_path)

if __name__ == "__main__":
    main()
