# 📍 Namma Ooru Smart Complaint AI

A deployed AI-powered civic complaint assistant for Bengaluru that analyzes uploaded images, validates civic issues, captures precise locations, and generates formal complaint drafts.

### 🚀 Live Demo
Check out the live web app here: [Launch App](https://smart-complaint-ai-c86a4xtfy8nfwh7ddjivwz.streamlit.app/)

### 🛠️ Key Engineering Features
* **Multimodal Validation Guardrail:** Pre-checks images to filter out invalid uploads (e.g., cats, unrelated text) before querying expensive content generation steps.
* **Resilient Multi-Model Fallback:** Catches `503 Server Overload` exceptions on experimental endpoints and seamlessly routes tracking logic through production-ready backup models without application downtime.
* **Interactive Geolocation Integration:** Renders a live Folium map layer to capture decimal coordinates and injects geographic context into automated text pipelines.
