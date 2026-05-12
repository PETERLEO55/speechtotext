import os, re, json, tempfile, streamlit as st
from streamlit_mic_recorder import mic_recorder
from google import genai
from google.genai import types
st.set_page_config( page_title="Voice Extractor", page_icon="🎙️", layout="centered" )
client = genai.Client(api_key=st.secrets["GEMINI_KEY"])
fields = ["Name", "Nationality", "Place_of_Issue"]
columns = {i: "" for i in fields}
if "results" not in st.session_state: st.session_state.results = columns.copy()
if "last_audio" not in st.session_state: st.session_state.last_audio = None
if "status" not in st.session_state: st.session_state.status = "idle"
if "last_extracted" not in st.session_state: st.session_state.last_extracted = {}
st.title("🎙️ Voice Field Extractor")
st.caption("Speak to fill fields. Speak again to correct.— Start & Stop.")
st.divider()
for label in fields:
    value = st.session_state.results.get(label, "") or "....."
    st.metric( label=label.replace("_", " "), value=value )
st.divider()
status = st.session_state.status
if status == "processing": st.warning("⏳ Processing your voice...")
elif status == "done":
    changed_fields = [k for k, v in st.session_state.last_extracted.items() if v]
    fields_str = ", ".join(changed_fields) if changed_fields else "no new fields"
    st.success(f"✅ Updated: {fields_str} — Speak again to correct anything.")
else:
    st.info("🎤 Ready — press Start and speak")
audio = mic_recorder( start_prompt="🎤  Start Recording", stop_prompt="⏹  Stop Recording", just_once=False, use_container_width=True, key="recorder" )
if audio and audio["bytes"] != st.session_state.last_audio:
    st.session_state.last_audio = audio["bytes"]
    st.session_state.status = "processing"
    with st.spinner("Processing..."):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio["bytes"])
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f: wav_bytes = f.read()
        os.unlink(tmp_path)
        prompt = f"""
        Listen carefully to the audio.
        Extract ONLY these fields: {fields}
        Rules:
        - Return STRICT JSON only — no markdown, no explanation
        - Replace any previously mentioned value with the latest spoken value
        - Leave field as empty string "" if not mentioned
        Example format:
        {json.dumps(columns, indent=2)}
        """
        response = client.models.generate_content( model="gemini-2.0-flash-lite", contents=[ prompt, types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav") ] )
        try:
            match = re.findall( r'```json\s*(\{.*?\})\s*```', response.text, re.DOTALL )
            text = match[0] if match else response.text
            data = json.loads(text)
            st.session_state.last_extracted = { k: v for k, v in data.items() if v }
            for k, v in data.items():
                if v: st.session_state.results[k] = v
            st.session_state.status = "done"
        except Exception as e:
            st.session_state.status = "idle"
            st.error(f"Parse error: {e} — raw: {response.text}")
    st.rerun()
st.divider()
st.download_button( label="⬇️  Download result.json", data=json.dumps(st.session_state.results, indent=4), file_name="result.json", mime="application/json", use_container_width=True )
if st.session_state.last_audio:
    with st.expander("🔈 Replay last recording"):
        st.audio(st.session_state.last_audio, format="audio/wav")
