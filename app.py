from dotenv import load_dotenv
import os, re, json, tempfile
from datetime import datetime as time
# load_dotenv(r'C:\Users\peter.leo\OneDrive - Qatar Insurance Group\Documents\Projects\OCR\5-3-2026-azure+llm\.env')
import streamlit as st
from streamlit_mic_recorder import mic_recorder
from google import genai
from google.genai import types
client = genai.Client(api_key=st.secrets["GEMINI_KEY"])
# client = genai.Client( api_key=os.getenv("GEMINI_KEY") )

fields = ["Name","Nationality","Place_of_Issue","Date_of_Birth","Expiry_date"]
columns = {i:" " for i in fields}

if "fields" not in st.session_state: st.session_state.fields = columns
if "last_audio" not in st.session_state: st.session_state.last_audio = None
if "show_audio" not in st.session_state: st.session_state.show_audio = False
st.title("Voice Assisted Key Value Extraction")
st.caption("Press **Start Recording**, speak clearly about your all details, then press **Stop Recording**.")
audio = mic_recorder( start_prompt="🎤  Start Recording", stop_prompt="⏹  Stop Recording", just_once=True, use_container_width=True, key="recorder" )
if audio:
    print(f'{time.now()}')
    with st.spinner("⏳ Audio is processing — please wait…"):
        st.session_state.last_audio = audio["bytes"]
        st.session_state.show_audio = False
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio["bytes"])
                tmp_path = tmp.name
        with open(tmp_path, "rb") as f: wav_bytes = f.read()
        os.unlink(tmp_path)
        prompt = f"""
        Listen carefully.
        Return STRICT JSON only - no explanation.
        Example:
        {json.dumps(columns, indent=2)}
        """
        response = client.models.generate_content( model="gemini-2.0-flash-lite", contents=[ prompt, types.Part.from_bytes( data=wav_bytes, mime_type="audio/wav") ] )
        
        match = re.findall(r'```json\s*(\{.*?\})\s*```', response.text, re.DOTALL)
        data = json.loads(match[0])
        st.session_state.fields = data
    st.success("✅ Extraction complete!")
    
st.divider()
for label, value in st.session_state.fields.items():
    col1, col2 = st.columns([1, 2])
    col1.markdown(f"**{label}**")
    st.session_state.fields[label] = col2.text_input(label, value=value, label_visibility="collapsed")


st.divider()
if st.session_state.last_audio:
    if st.button("▶ Use this to play back audio"):
        st.session_state.show_audio = not st.session_state.show_audio

    if st.session_state.show_audio:
        st.audio(st.session_state.last_audio, format="audio/wav")
