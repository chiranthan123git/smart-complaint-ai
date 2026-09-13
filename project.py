import streamlit as st
from google import genai
from google.genai import errors
from PIL import Image
import folium
from streamlit_folium import st_folium

# 1. Setup the Web Page Interface (Wide layout to support the map nicely)
st.set_page_config(page_title="Namma Ooru Smart Complaint", layout="wide", page_icon="📍")
st.title("📍 Namma Ooru Smart Complaint AI + Maps")
st.write(
    "Upload a photo of a local civic issue to automatically generate a formal complaint and capture precise map coordinates.")

# 2. Setup the AI Client
import os

# This looks for the hidden key on the cloud server
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)


# List of models we can fallback on if servers are overloaded
MODELS_TO_TRY = ['gemini-3.8-flash', 'gemini-3.6-flash']


# UNIVERSAL SAFE CALL FUNCTION
def safe_generate_content(client, contents):
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            return response, model_name
        except errors.ServerError as e:
            if "503" in str(e) and model_name != MODELS_TO_TRY[-1]:
                st.warning(f"⚠️ {model_name} overloaded. Automatically switching to stable backup model...")
                continue
            else:
                raise e
        except Exception as e:
            raise e


# Create a clean side-by-side layout (Column 1 for Inputs, Column 2 for Interactive Map)
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Step 1: Upload & Details")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    location_text = st.text_input("Enter the street name / area in Bengaluru (e.g., R.M.V. 2nd Stage):")

with col2:
    st.subheader("🗺️ Step 2: Pin the Exact Location")
    st.write("Click anywhere on the map to pin the exact coordinates of the issue.")

    # Initialize the map centered around R.M.V. 2nd Stage / Central Bengaluru
    # Latitude: 13.0308, Longitude: 77.5649 (R.M.V. 2nd Stage area baseline)
    m = folium.Map(location=[13.0308, 77.5649], zoom_start=14)

    # Enable a dynamic click-to-pin listener on the map
    m.add_child(folium.LatLngPopup())

    # Render the interactive map and capture its real-time click outputs
    map_data = st_folium(m, width=500, height=350)

    # Extract coordinates dynamically based on where the user clicks
    clicked_coords = None
    if map_data and map_data.get("last_clicked"):
        clicked_coords = map_data["last_clicked"]
        st.success(f"📍 Location Captured! Lat: {clicked_coords['lat']:.4f}, Lng: {clicked_coords['lng']:.4f}")

# Trigger processing block
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    with col1:
        st.image(image, caption="Uploaded Issue Preview", use_container_width=True)

    if st.button("Generate Formal Complaint ✨"):
        if API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            st.error("Please add your Gemini API Key in the code first!")
        elif not location_text:
            st.warning("Please provide a text location so the AI can draft an accurate letter.")
        else:
            with st.spinner("AI is analyzing the image and compiling geolocation data..."):
                try:
                    # STEP 1: VALIDATION GUARDRAIL
                    validation_prompt = """
                    Analyze this image. Is it a civic infrastructure or public maintenance issue? 
                    Examples: potholes, broken roads, garbage dumps, leaking sewage, broken streetlights.
                    Reply with exactly one word: 'VALID' or 'INVALID'.
                    """
                    check_response, active_model_1 = safe_generate_content(client, [image, validation_prompt])

                    if "INVALID" in check_response.text.strip().upper():
                        st.error(
                            "❌ Validation Failed: The uploaded image does not appear to show a public civic grievance. Please upload a relevant photo.")
                    else:
                        # STEP 2: DRAFT THE COMPLAINT (Now feeding map coordinates if available!)
                        st.info("🔄 Image verified successfully. Drafting your email...")

                        geo_string = ""
                        if clicked_coords:
                            geo_string = f"Exact GPS coordinates pinned by complainant: Latitude {clicked_coords['lat']:.5f}, Longitude {clicked_coords['lng']:.5f}."

                        complaint_prompt = f"""
                        You are an expert civic grievance officer in Bengaluru. 
                        Look at this uploaded image. Identify the specific civic issue. 
                        Write a formal, stern, yet polite complaint email addressed to the BBMP Commissioner / relevant authority.
                        Mention that this issue is located at: {location_text}. {geo_string}
                        Include placeholder brackets for [Your Name] and [Your Contact Number] at the end.
                        Keep the entire email concise and under 200 words. Do not use asterisks or markdown in your response.
                        """

                        response, active_model_2 = safe_generate_content(client, [image, complaint_prompt])

                        st.success("🎉 Complaint Generated Successfully!")
                        st.markdown("### 📋 Generated Draft Email:")

                        email_text = response.text
                        st.write(email_text)

                        # BUILT-IN COPY CONTAINER (Built-in standard copying layout widget)
                        st.text_area("📋 Copy text from the container below:", value=email_text, height=250)

                except Exception as e:
                    st.error(f"An error occurred: {e}")
