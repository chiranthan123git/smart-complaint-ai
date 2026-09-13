# 📍 Namma Ooru Smart Complaint AI

A production-grade cloud application that helps citizens in Bengaluru automatically generate formal civic complaints using Multimodal AI and interactive mapping tools.

### 🚀 Live Demo
Check out the live web app here: [Launch App](https://smart-complaint-ai-c86a4xtfy8nfwh7ddjivwz.streamlit.app/)

### 🛠️ Key Engineering Features
* **Multimodal Validation Guardrail:** Pre-checks images to filter out invalid uploads (e.g., cats, unrelated text) before querying expensive content generation steps.
* **Resilient Multi-Model Fallback:** Catches `503 Server Overload` exceptions on experimental endpoints and seamlessly routes tracking logic through production-ready backup models without application downtime.
* **Interactive Geolocation Integration:** Renders a live Folium map layer to capture decimal coordinates and injects geographic context into automated text pipelines.
