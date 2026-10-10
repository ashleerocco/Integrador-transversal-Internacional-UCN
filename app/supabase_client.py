"""Conexión a Supabase. Las credenciales se leen de .streamlit/secrets.toml."""
import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_client() -> Client:
    """Crea (una sola vez) el cliente de Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
