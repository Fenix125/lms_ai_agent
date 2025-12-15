import streamlit as st

from state import init_state, settings_ready, get_settings
from session import AgentSession, AsyncRunner
from settings_page import render_settings

st.set_page_config(page_title="LMS AI Assistant", layout="wide")

init_state()

def render_chat():
    st.title("LMS AI Assistant")
    st.subheader("Chat")

    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not settings_ready():
        st.info("Chat is disabled. Go to **Settings** and save your LMS username/password.")
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

        st.session_state["chat_messages"].append({"role": "assistant", "content": answer})


pages = [
    st.Page(render_chat, title="Assistant", icon=":material/smart_toy:", default=True),
    st.Page(render_settings, title="Settings", icon=":material/settings:"),
]
pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
