#!/usr/bin/env python
import sys
import os
import glob
import subprocess
import argparse
import asyncio
from pathlib import Path
from config import MainConfig, RelayConfig

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def migrate():
    """
    Runs the database migrations.
    """

    # Get migration files
    path = Path("./migrations")
    files = sorted(glob.glob(
        str(path / "*.py")
    ))

    if not files:
        raise ValueError(f"No migration files found in {path}")

    # Create migrations log directory if it doesn't exist
    log_dir = Path("/var/log/migrations")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Execute each migration file
    for file in files:
        filename = Path(file).name
        ok_path = Path(f"/var/log/migrations/{filename}.ok")
        error_path = Path(f"/var/log/migrations/{filename}.error")

        if ok_path.exists():
            continue

        if error_path.exists():
            print(f"WARNING: Migration '{file}' failed previously.")
            continue

        print(f"Migrating {file}...")

        try:
            # Execute file
            result = subprocess.run([
                "python",
                file
            ], capture_output=True, text=True, check=True, env={
                **os.environ,
                "PYTHONPATH": os.path.abspath(os.path.dirname(__file__))
            })
            
            # Print any output from the script
            if result.stdout:
                print(result.stdout.strip())

            print(f"done.")
            
            # Write .ok file
            with open(ok_path, 'w') as f:
                f.write(file)
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Error: {e.stderr.strip()}"
            print(error_msg)

            # Write .error file
            with open(error_path, 'w') as f:
                f.write(error_msg)
            
            print(f"failed.")
            return
        except Exception as e:
            error_msg = str(e)
            print(f"Error: {error_msg}")

            # Write .error file
            with open(error_path, 'w') as f:
                f.write(error_msg)
            
            print(f"failed.")
            return

def relay():
    """
    Runs the relay.
    """
    # Validate the configuration
    RelayConfig.validate()

    import relay.main as module
    asyncio.run(module.main())

def run(workers="1", host="localhost", port=8080, reload=False):
    """
    Runs the application.
    """
    # Validate the configuration
    MainConfig.validate()

    if reload:
        subprocess.run([
            "uvicorn",
            "app:asgi_app",
            "--host", host,
            "--port", str(port),
            "--reload",
            "--reload-dir", ".",
            "--reload-delay", "0.25",
            "--log-level", "debug"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
    else:
        subprocess.run([
            "gunicorn", 
            "--bind", f"{host}:{port}", 
            "--workers", workers,
            "--worker-class", "uvicorn.workers.UvicornWorker",
            "--env", "GUNICORN_WORKER_ID=${GUNICORN_WORKER_ID:-0}",
            "app:asgi_app"
        ])

def main():
    """
    Main function to parse arguments and run the appropriate command.
    """

    parser = argparse.ArgumentParser(description='Flask Management Script')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Migrate command
    subparsers.add_parser('migrate', help='Run database migrations')

    # Relay command
    subparsers.add_parser('relay', help='Run the relay')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run the application')
    run_parser.add_argument('--workers', default='1', help='Number of workers to run with Gunicorn')
    run_parser.add_argument('--host', default='localhost', help='Host to run the application on')
    run_parser.add_argument('--port', type=int, default=8080, help='Port to run the application on')
    run_parser.add_argument('--reload', action='store_true', help='Run with development server')

    args = parser.parse_args()

    if args.command == 'migrate':
        print("Applying migrations...")
        migrate()
    elif args.command == 'relay':
        print("Starting relay...")
        relay()
    elif args.command == 'run':
        print("Starting server...")
        print(f"Starting with reload: {args.reload}")
        run(args.workers, args.host, args.port, args.reload)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
