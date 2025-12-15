import streamlit as st
import uuid
import os
import atexit
import shutil

from state import init_state, settings_ready, get_settings
from session import AgentSession, AsyncRunner
from settings_page import render_settings
from pathlib import Path


def cleanup_uploads():
    """Clean up the ui_uploads folder on program exit."""
    upload_dir = Path.cwd() / "ui_uploads"
    if upload_dir.exists():
        shutil.rmtree(upload_dir)


atexit.register(cleanup_uploads)

st.set_page_config(page_title="LMS AI Assistant", layout="wide")

init_state()


def render_chat():
    st.title("LMS AI Assistant")
    st.subheader("Chat")

    # sidebar uploader only for Assistant page
    with st.sidebar:
        st.markdown("### Upload files for agent")

        # Check for duplicates in currently tracked files
        previous_paths = st.session_state.get("uploaded_file_paths", []) or []
        existing_names = {Path(p).name for p in previous_paths}

        uploaded_files = st.file_uploader(
            "Upload files",
            type=None,
            key="uploader_widget",
            accept_multiple_files=True,
        )

        # Show warning if user tries to upload files with duplicate names
        if uploaded_files:
            current_names = [f.name for f in uploaded_files]
            seen = set()
            duplicates_in_upload = []

            for name in current_names:
                if name in seen:
                    duplicates_in_upload.append(name)
                seen.add(name)

            if duplicates_in_upload:
                st.error(
                    f"🚫 Cannot upload duplicate files: {', '.join(set(duplicates_in_upload))}"
                )
                st.info("Please remove duplicate files from the uploader to continue.")
                # Don't process anything if there are duplicates
                uploaded_files = None

        upload_dir = Path.cwd() / "ui_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Get current uploaded file names
        current_file_names = (
            {f.name for f in uploaded_files} if uploaded_files else set()
        )

        # Get previously saved file paths
        previous_paths = st.session_state.get("uploaded_file_paths", []) or []
        previous_file_names = {Path(p).name for p in previous_paths}

        # Find files that were removed (in previous but not in current)
        removed_files = previous_file_names - current_file_names

        # Delete removed files
        for file_path in previous_paths:
            if Path(file_path).name in removed_files and os.path.exists(file_path):
                os.remove(file_path)

        # Save new files and update session state
        if uploaded_files:
            saved_paths = []

            for uploaded_file in uploaded_files:
                saved_path = upload_dir / uploaded_file.name
                saved_path.write_bytes(uploaded_file.getbuffer())
                saved_paths.append(str(saved_path))

            st.session_state["uploaded_file_paths"] = saved_paths

            st.caption(f"Saved {len(saved_paths)} file(s):")
            for path in saved_paths:
                st.caption(f"`{Path(path).name}`")
        else:
            st.session_state["uploaded_file_paths"] = None

    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not settings_ready():
        st.info(
            "Chat is disabled. Go to **Settings** and save your LMS username/password."
        )
        st.stop()

    if st.session_state.get("agent_session") is None:
        st.session_state["agent_session"] = AgentSession(runner=AsyncRunner())

    ui = get_settings()

    def on_send():
        txt = st.session_state.get("chat_input", "")
        if txt:
            st.session_state["pending_user_text"] = txt
            st.session_state["chat_input"] = ""

    st.chat_input("Message the agent...", key="chat_input", on_submit=on_send)
    user_text = st.session_state.get("pending_user_text")
    if user_text:
        st.session_state["pending_user_text"] = None

    if user_text:
        file_paths = st.session_state.get("uploaded_file_paths")
        if file_paths:
            user_text = f"{user_text}\n\n"
            for file_path in file_paths:
                user_text += f"[UPLOADED_FILE_PATH]: {file_path}\n"

        st.session_state["chat_messages"].append({"role": "user", "content": user_text})

        with st.chat_message("user"):
            st.write(user_text)

        sess: AgentSession = st.session_state["agent_session"]

        with st.chat_message("assistant"):
            out = st.empty()

            with st.spinner("Thinking..."):
                ok, err = sess.ensure_started(
                    ui_username=ui.lms_username,
                    ui_password=ui.lms_password,
                    show_realtime=ui.show_realtime,
                )
                if not ok:
                    answer = f"Login/session initialization failed: {err}"
                else:
                    try:
                        answer = sess.ask(user_text)
                    except Exception as e:
                        answer = f"Agent error: {e}"

                out.write(answer)

        st.session_state["chat_messages"].append(
            {"role": "assistant", "content": answer}
        )


pages = [
    st.Page(render_chat, title="Assistant", icon=":material/smart_toy:", default=True),
    st.Page(render_settings, title="Settings", icon=":material/settings:"),
]
pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
