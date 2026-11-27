"""Obtiene el refresh_token para que la app suba archivos al Drive de tu cuenta Google.

Uso (una sola vez, en tu computador):
    pip install google-auth-oauthlib
    python obtener_token_drive.py ruta/al/client_secret.json

Se abre el navegador, inicias sesión con la cuenta dueña de la carpeta "A+S Idiomas"
y aceptas. El script imprime el bloque [google_oauth] para pegar en .streamlit/secrets.toml.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

if len(sys.argv) != 2:
    sys.exit("Uso: python obtener_token_drive.py client_secret.json")

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
cred = flow.run_local_server(port=0, access_type="offline", prompt="consent")
if not cred.refresh_token:
    sys.exit("Google no entregó refresh_token. Quita el acceso de la app en tu cuenta y repite.")

print("\nPega esto en .streamlit/secrets.toml (NO lo subas a GitHub):\n")
print("[google_oauth]")
print(f"client_id = {json.dumps(cred.client_id)}")
print(f"client_secret = {json.dumps(cred.client_secret)}")
print(f"refresh_token = {json.dumps(cred.refresh_token)}")
