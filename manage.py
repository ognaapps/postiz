#!/usr/bin/env python3
import subprocess
import sys
import secrets
import string

PROJECT_NAME = "postiz"


def generate_clear_password(length=100):
    ambiguous = {'O', '0', 'I', 'l', '1'}
    alphabet = ''.join(c for c in (string.ascii_letters + string.digits) if c not in ambiguous)
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def parse_args(argv):
    args = {}
    key = None
    for item in argv:
        if item.startswith("--"):
            key = item.lstrip("-")
            args[key] = True  # default if no value provided
        elif key:
            args[key] = item
            key = None
    return args


def up():
    """Start docker compose services"""
    subprocess.run(["mkdir", "-p", f"/mnt/volume-db/{PROJECT_NAME}/redis"], check=True)
    subprocess.run(["mkdir", "-p", f"/mnt/volume-db/{PROJECT_NAME}/postgress"], check=True)    
    subprocess.run(["docker", "compose", "-p", PROJECT_NAME, "up", "-d"], check=True)


def down():
    """Stop docker compose services and remove volumes"""
    subprocess.run(["docker", "compose", "-p", PROJECT_NAME, "down", "-v"], check=True)


class ComposeApp:

    def __init__(self, action, user, host, protocol):
        self.action = action
        self.user = user
        self.host = host
        self.protocol = protocol
        self.env_variables = {
            'POSTGRES_USER': "postiz-user",
            'POSTGRES_PASSWORD': generate_clear_password(),
            'POSTGRES_DB': "postiz-db-local",
            'OGNA_USER':user,
            'OGNA_HOST':host,
            'OGNA_PROTOCOL':protocol,
            'MAIN_URL': f"{self.protocol}://{PROJECT_NAME}.{self.user}.{self.host}",
            'FRONTEND_URL': f"{self.protocol}://{PROJECT_NAME}.{self.user}.{self.host}",
            'NEXT_PUBLIC_BACKEND_URL': f"{self.protocol}://{PROJECT_NAME}.{self.user}.{self.host}/api",
            'JWT_SECRET': generate_clear_password(),
            'REDIS_URL': "redis://postiz-redis:6379",
            'BACKEND_INTERNAL_URL': "http://localhost:3000",
            'IS_GENERAL': "true",
            'DISABLE_REGISTRATION': "true",
            # === Storage Settings
            'STORAGE_PROVIDER': "local",
            'UPLOAD_DIRECTORY': "/uploads",
            'NEXT_PUBLIC_UPLOAD_DIRECTORY': "/uploads",
            'POSTIZ_GENERIC_OAUTH': "true",
            'POSTIZ_OAUTH_CLIENT_ID': generate_clear_password(30),
            'POSTIZ_OAUTH_CLIENT_SECRET': generate_clear_password(),                      
        }

        self.env_variables['DATABASE_URL'] = f"postgresql://{self.env_variables['POSTGRES_USER']}:{self.env_variables['POSTGRES_PASSWORD']}@postiz-postgres:5432/{self.env_variables['POSTGRES_DB']}"

    def configure(self):
        with open('.env', 'w+') as env_file:
            for key, value in self.env_variables.items():
                env_file.write(f"{key}={value}")
                env_file.write("\n")

    def deploy(self):
        self.configure()
        if self.action == "up":
            up()
        elif self.action == "down":
            down()
        else:
            print(f"Unknown command: {self.action}")
            print("Available commands: up, down")
            sys.exit(1)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    app = ComposeApp(
        action=args.get("action"),
        user=args.get("user", 'user'),
        host=args.get("host", 'localhost'),
        protocol=args.get("protocol", 'http')
    )

    app.deploy()
