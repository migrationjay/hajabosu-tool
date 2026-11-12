"""담당자 화면 (내 PC). 접수 원문이 하자대장이 되는 과정을 단계별로 보여준다.
실행: streamlit run app.py
"""
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import ai
import rules
import run

BASE = Path(__file__).parent
접수함 = BASE / "data" / "접수함"

st.set_page_config(page_title="하자보수 접수 처리", layout="wide")
st.title("하자보수 접수 처리")
st.caption("접수 원문 → 🤖 AI가 읽고 정리 → ⚙️ 코드가 번호·기한·보증 판정 → 👤 사람이 확인 → 하자대장")

공사목록 = rules.공사정보_읽기()
파일들 = sorted(접수함.glob("*.txt"))
if "정리" not in st.session_state:
    st.session_state.정리 = {}  # 파일명 -> AI가 정리한 5칸


def 정리하기(파일):
    try:
        with st.spinner(f"AI가 {파일.name}을(를) 읽는 중..."):
            st.session_state.정리[파일.name] = ai.접수정리(파일.name, 파일.read_text(encoding="utf-8"))
        return True
    except Exception as e:  # 키 오류·네트워크·AI 답 형식 오류를 화면에 그대로 보여준다.
        st.error(f"{파일.name} 처리 실패: {e}")
        return False


def 대장_행들():
    """정리된 접수를 파일명 순서로 훑으며 접수일별 순번을 매겨 하자대장 행을 만든다."""
    순번 = defaultdict(int)
    행들 = []
    for 파일 in 파일들:
        정리 = st.session_state.정리.get(파일.name)
        if not 정리:
            continue
        순번[정리["접수일"]] += 1
        행들.append(run.행_만들기(파일.name, 정리, 순번[정리["접수일"]], 공사목록))
    return 행들


# ── 0. 접수 고르기 ──
st.header("0. 접수함")
if not 파일들:
    st.warning("data/접수함에 접수 원문(.txt)이 없습니다.")
    st.stop()

좌, 우 = st.columns([2, 1])
with 좌:
    선택이름 = st.selectbox(
        "접수 원문 파일", [p.name for p in 파일들],
        format_func=lambda n: f"{n}  " + ("✅ 처리됨" if n in st.session_state.정리 else ""),
    )
    선택 = 접수함 / 선택이름
with 우:
    st.write("")
    st.write("")
    b1, b2 = st.columns(2)
    if b1.button("이 접수 처리", type="primary", use_container_width=True):
        정리하기(선택)
    if b2.button(f"{len(파일들)}건 모두 처리", use_container_width=True):
        for p in 파일들:
            if p.name not in st.session_state.정리 and not 정리하기(p):
                break

행들 = 대장_행들()
내행 = next((r for r in 행들 if r["원문파일"] == 선택.name), None)

st.subheader("접수 원문")
st.code(선택.read_text(encoding="utf-8"), language=None, wrap_lines=True)

if not 내행:
    st.info("위의 [이 접수 처리] 버튼을 누르면 아래에 처리 과정이 나타납니다.")
else:
    정리 = st.session_state.정리[선택.name]

    # ── 1. AI ──
    st.header("1. 🤖 AI가 원문을 읽고 5칸으로 정리")
    st.caption("문장을 읽고 해석하는 일만 AI가 합니다. 지침: 지침/접수정리.md")
    st.dataframe(pd.DataFrame([정리]), hide_index=True, use_container_width=True)
    if len(정리["하자내용"]) > 40:
        st.warning(f"하자내용이 40자를 넘습니다({len(정리['하자내용'])}자).")

    # ── 2. 코드 ──
    st.header("2. ⚙️ 코드가 번호·기한·보증을 계산")
    st.caption("규칙대로 계산하는 일은 코드가 합니다(rules.py). AI는 관여하지 않습니다.")
    접수일 = date.fromisoformat(정리["접수일"])

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**접수번호**")
        st.write(f"`{내행['접수번호']}` — 같은 접수일 안에서 접수 순서대로 순번을 올립니다.")
    with c2:
        일수 = rules.조치기한_일수.get(정리["긴급도"])
        st.markdown("**조치기한**")
        st.write(f"접수일 {정리['접수일']} + {일수}일 (긴급도 {정리['긴급도']}) = `{내행['조치기한']}`")

    st.markdown("**보증 판정** (기준은 오늘이 아니라 접수일)")
    후보 = rules.후보공사(정리["위치"], 정리["공종"], 공사목록)
    st.write(f"① 공사정보에서 위치 `{정리['위치']}`, 공종 `{정리['공종']}` 조건에 모두 맞는 공사를 찾습니다 → **{len(후보)}건**")
    if 후보:
        표 = pd.DataFrame(후보)[["공사번호", "공사명", "시공업체", "준공일", "하자보증기간(년)"]]
        표["보증만료일"] = [rules.보증만료일(r["준공일"], r["하자보증기간(년)"]).isoformat() for r in 후보]
        st.dataframe(표, hide_index=True, use_container_width=True)

    if 내행["보증판정"] == "확인필요":
        사유 = "공종이 하나로 정해지지 않았습니다" if len(rules._후보_공종(정리["공종"])) != 1 else (
            "맞는 공사가 없습니다" if not 후보 else "맞는 공사가 2건 이상입니다")
        st.write(f"② {사유} → 코드가 정하지 않고 **확인필요**로 남깁니다.")
    else:
        만료 = date.fromisoformat(내행["보증만료일"])
        st.write(
            f"② 보증만료일 = 준공일 {내행['준공일']} + 보증기간 → `{내행['보증만료일']}`\n\n"
            f"③ 접수일 {정리['접수일']} {'≤' if 접수일 <= 만료 else '>'} 보증만료일 {내행['보증만료일']} "
            f"→ **{내행['보증판정']}**, 책임구분 **{내행['책임구분']}**"
        )
    if 내행["비고"]:
        st.info(f"비고: {내행['비고']} — 만료 전에 꼭 요청해야 합니다.")

    # ── 3. 사람 ──
    st.header("3. 👤 사람이 확인")
    if 내행["상태"] == "확인필요":
        st.warning("현장을 보고 공종·공사를 정해야 하는 건입니다. 담당자가 확인하세요.")
    else:
        st.success("판정이 끝났습니다. 내용을 확인한 뒤 조치요청으로 넘기세요(공문 단계는 아직 없음).")

# ── 4. 하자대장 ──
st.header("4. 하자대장")
if 행들:
    st.dataframe(pd.DataFrame(행들)[run.대장_칸], hide_index=True, use_container_width=True)
    if st.button("DB 하자대장에 저장"):
        run.저장(행들)
        st.success(f"DB 하자대장에 저장했습니다 ({len(행들)}건)")
else:
    st.caption("처리한 접수가 아직 없습니다.")
