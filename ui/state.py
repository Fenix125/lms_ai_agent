from __future__ import annotations

from dataclasses import dataclass
import streamlit as st


@dataclass(frozen=True)
class UISettings:
    lms_username: str
    lms_password: str
    show_realtime: bool


def init_state() -> None:
    st.session_state.setdefault("settings_saved", False)
    st.session_state.setdefault("lms_username", "")
    st.session_state.setdefault("lms_password", "")
    st.session_state.setdefault("show_realtime", False)

    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("agent_session", None)
    st.session_state.setdefault("pending_user_text", None)
    st.session_state.setdefault("uploaded_file_paths", None)


def settings_ready() -> bool:
    return (
        bool(st.session_state.get("settings_saved"))
        and bool(st.session_state.get("lms_username"))
        and bool(st.session_state.get("lms_password"))
    )


def get_settings() -> UISettings:
    return UISettings(
        lms_username=st.session_state.get("lms_username", "").strip(),
        lms_password=st.session_state.get("lms_password", ""),
        show_realtime=bool(st.session_state.get("show_realtime", False)),
    )
