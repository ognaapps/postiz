#!/usr/bin/env python3
import subprocess
import sys
import secrets
import string
import os
import json

PROJECT_NAME = "postiz"
VOLUMES = ['redis','postgress']


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
    for vol in VOLUMES:
        subprocess.run(["mkdir", "-p", f"/mnt/volume-db/{PROJECT_NAME}/{vol}"], check=True)
    subprocess.run(["docker", "compose", "-p", PROJECT_NAME, "up", "-d"], check=True)

def restart():
    """Docker restarts"""
    subprocess.run(["docker", "compose", "-p", PROJECT_NAME, "up", "-d","--force-recreate"], check=True)

def down():
    """Stop docker compose services and remove volumes"""
    subprocess.run(["docker", "compose", "-p", PROJECT_NAME, "down", "-v"], check=True)

def get_smtp_secrets():
    path = "/mnt/volume-db/secrets/smtp.json"
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"SMTP config file not found at: {path}")
    
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {path}: {e}")

def get_user_data():
    path = "/mnt/volume-db/secrets/user.json"
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"user config file not found at: {path}")
    
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {path}: {e}")

def load_env_file(path):
    """
    Reads a .env file and returns its contents as a dictionary.
    Lines starting with # are ignored.
    """
    env_vars = {}

    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments or empty lines
                if not line or line.startswith("#"):
                    continue

                # Split only on the first '='
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        return {}

    return env_vars


class ComposeApp:

    def __init__(self, action, user, host, protocol):
        self.action = action
        self.user = user
        self.host = host
        self.protocol = protocol
        self.smtp_data = {}
        existing_vars =load_env_file('.env')

        try:
            self.smtp_data = get_smtp_secrets()
        except Exception as e:
            print(e)
            sys.exit(1)

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
            'EMAIL_PROVIDER':"brevo",
            'EMAIL_HOST':self.smtp_data['host'],
            'EMAIL_PORT':self.smtp_data['port'],
            'EMAIL_SECURE':True if str(self.smtp_data['ssl']).lower() in [1,'true',True] else False,
            'EMAIL_USER':self.smtp_data['user'],
            'EMAIL_PASS':self.smtp_data['password'],
            'EMAIL_FROM_NAME':"Ogna",
            'EMAIL_FROM_ADDRESS':self.smtp_data['sender']                      
        }

        for key, value in self.env_variables.items():
            self.env_variables[key] = existing_vars.get(key,value)

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
        elif self.action == "restart":
            restart()            
        else:
            print(f"Unknown command: {self.action}")
            print("Available commands: up, down, restart")
            sys.exit(1)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    user_data= get_user_data()

    app = ComposeApp(
        action=args.get("action"),
        user=user_data.get('user',args.get("user", 'user')),
        host=user_data.get('host',args.get("host", 'host')),
        protocol=user_data.get('protocol',args.get("protocol", 'protocol'))
    )

    app.deploy()
