import streamlit as st

from state import init_state


def render_settings():
    init_state()
    st.title("LMS AI Assistant")
    st.subheader("Settings")

    username = st.text_input("LMS username", value=st.session_state.get("lms_username", ""))
    password = st.text_input("LMS password", value=st.session_state.get("lms_password", ""), type="password")
    show_realtime = st.checkbox("Show realtime agent actions", value=bool(st.session_state.get("show_realtime", False)))

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        if st.button("Save", type="primary", use_container_width=True):
            st.session_state["lms_username"] = username.strip()
            st.session_state["lms_password"] = password
            st.session_state["show_realtime"] = show_realtime
            st.session_state["settings_saved"] = bool(username.strip()) and bool(password)

            sess = st.session_state.get("agent_session")
            if sess is not None:
                try:
                    sess.stop()
                except Exception:
                    pass
                st.session_state["agent_session"] = None

            st.success("Saved")

    with col2:
        if st.button("Clear saved credentials", use_container_width=True, width="stretch"):
            st.session_state["lms_username"] = ""
            st.session_state["lms_password"] = ""
            st.session_state["show_realtime"] = False
            st.session_state["settings_saved"] = False

            sess = st.session_state.get("agent_session")
            if sess is not None:
                try:
                    sess.stop()
                except Exception:
                    pass
            st.session_state["agent_session"] = None
            st.success("Cleared")
