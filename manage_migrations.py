import os
import sys
import argparse
import subprocess
from datetime import datetime

def run_command(command):
    process = subprocess.Popen(command, shell=True)
    process.communicate()
    return process.returncode

def create_migration(message=None):
    if not message:
        message = f"Migration {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    cmd = f"alembic revision --autogenerate -m \"{message}\""
    return run_command(cmd)

def upgrade(revision="head"):
    cmd = f"alembic upgrade {revision}"
    return run_command(cmd)

def downgrade(revision="-1"):
    cmd = f"alembic downgrade {revision}"
    return run_command(cmd)

def main():
    parser = argparse.ArgumentParser(description="Database migration management")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("-m", "--message", help="Migration message")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument("revision", nargs="?", default="head", help="Revision to upgrade to")
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", nargs="?", default="-1", help="Revision to downgrade to")
    
    args = parser.parse_args()
    
    if args.command == "create":
        return create_migration(args.message)
    elif args.command == "upgrade":
        return upgrade(args.revision)
    elif args.command == "downgrade":
        return downgrade(args.revision)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())