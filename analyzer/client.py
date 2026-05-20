import streamlit as st
from google import genai


@st.cache_resource
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)
