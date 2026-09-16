import streamlit as st
from google import genai
from google.genai import errors
from PIL import Image
import folium
from streamlit_folium import st_folium
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from geopy.geocoders import Nominatim  # NEW: For address detection

# 1. Setup the Web Page Interface
st.set_page_config(page_title="Namma Ooru Smart Complaint", layout="wide", page_icon="📍")
st.title("📍 Namma Ooru Smart Complaint AI + Auto-Location")
st.write(
    "Upload a photo of a local civic issue, click the map to instantly auto-detect the address, and dispatch your complaint.")

# Make sure these lines exist near the top of your file!
import os

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = os.environ.get("GEMINI_API_KEY", "")

# THIS IS THE MISSING LINE!
client = genai.Client(api_key=API_KEY)


MODELS_TO_TRY = ['gemini-3.8-flash', 'gemini-3.6-flash']


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


# AUTOMATED EMAIL ENGINE
def send_automated_email(sender_email, app_password, receiver_email, subject, body):
    smtp_server="smtp.gmail.com"
    smtp_port=587
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, app_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)


# Initialize Session State variables to store the address across map clicks
if 'auto_address' not in st.session_state:
    st.session_state['auto_address'] = ""

# Layout Columns
col1, col2 = st.columns(2)

with col2:
    st.subheader("🗺️ Step 2: Pin the Exact Location")
    st.write("Click anywhere on the map to auto-fill the address details below.")

    # Initialize map around central Bangalore / RMV 2nd stage
    m = folium.Map(location=[13.0308, 77.5649], zoom_start=14)
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, width=500, height=350)

    clicked_coords = None
    if map_data and map_data.get("last_clicked"):
        clicked_coords = map_data["last_clicked"]

        # NEW LOGIC: Reverse Geocoding via Geopy
        try:
            # Setting a unique user_agent is required by OpenStreetMap policies
            geolocator = Nominatim(user_agent="namma_ooru_civic_tech_app")
            location_object = geolocator.reverse((clicked_coords['lat'], clicked_coords['lng']), timeout=10)

            if location_object:
                # Store the real-world address string in Session State
                st.session_state['auto_address'] = location_object.address
            else:
                st.session_state['auto_address'] = f"Lat: {clicked_coords['lat']:.5f}, Lng: {clicked_coords['lng']:.5f}"
        except Exception as e:
            st.session_state['auto_address'] = f"Lat: {clicked_coords['lat']:.5f}, Lng: {clicked_coords['lng']:.5f}"

with col1:
    st.subheader("📸 Step 1: Upload & Details")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    # NEW LOGIC: The text input box is now dynamically fed by the map click value!
    location_text = st.text_input(
        "Detected Address / Area (Review or modify if needed):",
        value=st.session_state['auto_address']
    )

# Trigger processing block
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    with col1:
        st.image(image, caption="Uploaded Issue Preview", use_container_width=True)

    if st.button("Generate Formal Complaint ✨"):
        if API_KEY == "YOUR_GEMINI_API_KEY_HERE" or API_KEY == "":
            st.error("Please ensure your Gemini API Key environment variable is configured!")
        elif not location_text:
            st.warning("Please pin a location on the map or type an area description.")
        else:
            with st.spinner("AI is analyzing the image and determining correct department..."):
                try:
                    # STEP 1: VALIDATION GUARDRAIL
                    validation_prompt = """
                    Analyze this image. Is it a civic infrastructure or public maintenance issue? 
                    Reply with exactly one word: 'VALID' or 'INVALID'.
                    """
                    check_response, active_model_1 = safe_generate_content(client, [image, validation_prompt])

                    if "INVALID" in check_response.text.strip().upper():
                        st.error(
                            "❌ Validation Failed: The uploaded image does not appear to show a public civic grievance.")
                    else:
                        # NEW: STEP 1.5 - SMART AI EMAIL ROUTING ENGINE
                        routing_prompt = """
                        Analyze this civic issue image and categorize which Bengaluru municipal department must handle it.
                        Follow these rules strictly:
                        - Reply 'BESCOM' if it involves electricity, sparking transformers, hanging power wires, or fallen electric poles.
                        - Reply 'BWSSB' if it involves leaking water mains, open manholes, or overflowing sewage/drainage.
                        - Reply 'BBMP' for anything else (potholes, garbage piles, broken footpaths, bad roads).
                        Reply with exactly one word from these three options: BBMP, BESCOM, or BWSSB.
                        """
                        route_response, active_model_route = safe_generate_content(client, [image, routing_prompt])
                        detected_dept = route_response.text.strip().upper()

                        # Dynamic email map assignment based on AI classification string
                        email_directory = {
                            "BBMP": "bbmp.grievance@example.com",
                            "BESCOM": "bescom.safety@example.com",
                            "BWSSB": "bwssb.water@example.com"
                        }

                        # Fallback default if AI output contains extra characters
                        target_dept = "BBMP"
                        for dept in email_directory.keys():
                            if dept in detected_dept:
                                target_dept = dept
                                break

                        st.session_state['assigned_dept'] = target_dept
                        st.session_state['assigned_email'] = email_directory[target_dept]
                        st.info(f"🤖 AI Smart Routing: Categorized under **{target_dept}**.")

                        # STEP 2: DRAFT THE COMPLAINT
                        geo_string = ""
                        if clicked_coords:
                            geo_string = f"Exact GPS coordinates pinned by complainant: Latitude {clicked_coords['lat']:.5f}, Longitude {clicked_coords['lng']:.5f}."

                        complaint_prompt = f"""
                        You are an expert civic grievance officer in Bengaluru. 
                        Identify the specific civic issue in the uploaded image.
                        Write a formal, stern, yet polite complaint email addressed to the {target_dept} Commissioner.
                        Mention that this issue is located at: {location_text}. {geo_string}
                        Keep the entire email concise and under 200 words. Do not use asterisks or markdown formatting.
                        """

                        response, active_model_2 = safe_generate_content(client, [image, complaint_prompt])
                        st.session_state['draft_email'] = response.text
                        st.success("🎉 Complaint Generated Successfully!")

                except Exception as e:
                    st.error(f"An error occurred: {e}")

# STEP 3: THE AUTOMATION PANEL
if 'draft_email' in st.session_state:
    st.markdown("---")
    st.subheader("🚀 Step 3: Review & Automated Dispatch")
    final_email_body = st.text_area("Edit your complaint if needed before sending:",
                                    value=st.session_state['draft_email'], height=250)

    c1, c2, c3 = st.columns(3)
    with c1:
        user_email = st.text_input("Your Gmail Address (Sender):", placeholder="example@gmail.com")
    with c2:
        user_app_pass = st.text_input("Your 16-Character App Password:", type="password")
    with c3:
        # NEW: The value now dynamically responds to the AI session state mapping!
        default_email = st.session_state.get('assigned_email', 'bbmp.grievance@example.com')
        target_email = st.text_input("Authority Email (Receiver):", value=default_email)

    if st.button("Directly Mail to Authority ✉️"):
        if not user_email or not user_app_pass:
            st.warning("Please provide your automated sender credentials.")
        else:
            with st.spinner("Opening secure TLS link..."):
                success, message = send_automated_email(
                    sender_email=user_email,
                    app_password=user_app_pass,
                    receiver_email=target_email,
                    subject=f"URGENT: Civic Infrastructure Grievance at {location_text[:50]}...",
                    body=final_email_body
                )
                if success:
                    st.success("🚀 The complaint email has been successfully signed, encrypted, and dispatched!")
                else:
                    st.error(f"Failed to transmit email: {message}")
