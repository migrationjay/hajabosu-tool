"""AI 호출은 이 파일에서만 한다. 키와 모델은 .env에서 읽는다."""
import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

접수정리_칸 = ["접수일", "위치", "공종", "하자내용", "긴급도"]


def _client():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(".env에 ANTHROPIC_API_KEY가 없습니다.")
    return anthropic.Anthropic()


def _model():
    model = os.getenv("MODEL")
    if not model:
        raise RuntimeError(".env에 MODEL이 없습니다.")
    return model


def ask(지침파일, 사용자글, max_tokens=4096):
    """지침/ 폴더의 지침 파일을 시스템 프롬프트로 주고 답 글을 돌려준다."""
    system = (BASE / "지침" / 지침파일).read_text(encoding="utf-8")
    response = _client().messages.create(
        model=_model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": 사용자글}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("AI가 답을 거절했습니다.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("AI 답이 길이 제한에서 잘렸습니다.")
    return "".join(b.text for b in response.content if b.type == "text")


def 접수정리(파일명, 원문):
    """접수 원문 1건 -> {접수일, 위치, 공종, 하자내용, 긴급도}"""
    답 = ask("접수정리.md", f"파일명: {파일명}\n\n접수 원문:\n{원문}")
    match = re.search(r"\{.*\}", 답, re.S)
    if not match:
        raise ValueError(f"AI 답에서 JSON을 찾지 못했습니다: {답!r}")
    결과 = json.loads(match.group(0))
    빠진 = [k for k in 접수정리_칸 if k not in 결과]
    if 빠진:
        raise ValueError(f"AI 답에 빠진 칸이 있습니다: {빠진}")
    return {k: 결과[k] for k in 접수정리_칸}


if __name__ == "__main__":
    # 사용: python ai.py data/접수함/01_20261102_B1푸드코트_누수.txt
    path = Path(sys.argv[1])
    결과 = 접수정리(path.name, path.read_text(encoding="utf-8"))
    print(json.dumps(결과, ensure_ascii=False, indent=2))
