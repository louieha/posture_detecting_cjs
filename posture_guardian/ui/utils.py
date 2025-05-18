"""ui.utils
UI 헬퍼 함수 모음 (CSS 로드 등)
"""
from pathlib import Path
import streamlit as st


def load_css():
    """외부 CSS 파일(ui/style.css)을 읽어 페이지에 적용합니다."""
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning("style.css 파일을 찾을 수 없습니다. UI가 기본 스타일로 표시됩니다.") 