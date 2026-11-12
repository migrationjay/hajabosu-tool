"""접수 화면. 접수 내용을 DB 접수 테이블에 저장한다. (처리는 run.py가 한다)
실행: python -m streamlit run intake.py
"""
from datetime import date

import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="하자 접수", layout="centered")
st.title("하자 접수")
st.caption("접수 내용을 적어 저장하면 '미처리' 접수가 됩니다. 발견일이 하자대장의 접수일이 됩니다.")

with st.form("접수", clear_on_submit=True):
    발견일 = st.date_input("발견일", value=date.today(), max_value=date.today())
    c1, c2 = st.columns(2)
    접수자 = c1.text_input("접수자")
    부서 = c2.text_input("부서")
    위치 = st.text_input("위치", placeholder="예: 2F 화장실")
    내용 = st.text_area("내용", placeholder="무엇이 어떻게 문제인지 적어주세요.", height=140)
    보냄 = st.form_submit_button("접수 저장", type="primary")

if 보냄:
    if not 내용.strip():
        st.error("내용을 적어주세요.")
    else:
        새id = db.접수_저장(발견일, 접수자.strip(), 부서.strip(), 위치.strip(), 내용.strip())
        st.success(f"접수했습니다 (접수 id {새id}, 발견일 {발견일}). 처리는 run.py가 합니다.")

st.subheader("접수 목록")
접수들 = db.접수_읽기()
if 접수들:
    st.dataframe(pd.DataFrame(접수들[::-1]), hide_index=True, width="stretch")
else:
    st.caption("접수가 아직 없습니다.")
