#!/usr/bin/env python
from config import Config
import subprocess
import argparse
import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def run(workers="1", host="localhost", port=8080, reload=False):
    """
    Runs the application.
    """
    # Validate the configuration
    Config.validate()

    if reload:
        # Get the app instance
        from app import create_app
        app = create_app()
        # Use the built-in Flask development server which works with flask-sock
        app.run(host=host, port=port, debug=True, extra_files=['templates/**/*.html', 'static/**/*.scss'])
    else:
        subprocess.run([
            "gunicorn", 
            "--bind", f"{host}:{port}", 
            "--workers", workers,
            "--worker-class", "gevent",
            "app:app"
        ])

def main():
    """
    Main function to parse arguments and run the appropriate command.
    """

    parser = argparse.ArgumentParser(description='Flask Management Script')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run the application')
    run_parser.add_argument('--workers', default='1', help='Number of workers to run with Gunicorn')
    run_parser.add_argument('--host', default='localhost', help='Host to run the application on')
    run_parser.add_argument('--port', type=int, default=8080, help='Port to run the application on')
    run_parser.add_argument('--reload', action='store_true', help='Run with development server')

    args = parser.parse_args()

    if args.command == 'run':
        print("Starting server...")
        print(f"Starting with reload: {args.reload}")
        run(args.workers, args.host, args.port, args.reload)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
