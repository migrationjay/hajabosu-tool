"""접수함 폴더의 접수 원문을 일괄 처리해 하자대장.csv로 저장한다.

흐름: 원문 읽기 -> AI가 5칸 정리(ai.py) -> 코드가 번호·기한·보증 판정(rules.py) -> CSV 저장
사용: python run.py [입력폴더] [저장파일]
"""
import sys
from collections import defaultdict
from pathlib import Path

import ai
import db
import rules

BASE = Path(__file__).parent
대장_칸 = db.대장_칸


def 행_만들기(파일명, 정리, 순번, 공사목록):
    """AI가 정리한 5칸 + 접수일별 순번 -> 하자대장 1행 (번호·기한·판정은 rules.py)"""
    판정 = rules.보증판정(정리["접수일"], 정리["위치"], 정리["공종"], 공사목록)
    return {
        "접수번호": rules.접수번호(정리["접수일"], 순번),
        "접수일": 정리["접수일"],
        "원문파일": 파일명,
        "위치": 정리["위치"],
        "공종": 정리["공종"],
        "하자내용": 정리["하자내용"],
        "긴급도": 정리["긴급도"],
        "조치기한": rules.조치기한(정리["접수일"], 정리["긴급도"]),
        **판정,
        "상태": "확인필요" if 판정["보증판정"] == "확인필요" else "판정완료",
    }


def 처리(입력폴더, 공사목록):
    순번 = defaultdict(int)  # 접수일별 순번
    행들 = []
    for 파일 in sorted(Path(입력폴더).glob("*.txt")):
        정리 = ai.접수정리(파일.name, 파일.read_text(encoding="utf-8"))
        순번[정리["접수일"]] += 1
        행 = 행_만들기(파일.name, 정리, 순번[정리["접수일"]], 공사목록)
        if len(행["하자내용"]) > 40:
            print(f"[주의] {파일.name}: 하자내용이 40자를 넘습니다({len(행['하자내용'])}자)")
        행들.append(행)
        print(f"{행['접수번호']} {파일.name} -> {행['공종']} / {행['긴급도']} / {행['보증판정']}")
    return 행들


def 저장(행들, 저장파일=None):
    """하자대장은 DB에 저장한다(db.py). 저장파일은 예전 호출과 맞추려고 남긴 자리이며 쓰지 않는다."""
    db.대장_저장(행들)


if __name__ == "__main__":
    입력 = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "data" / "접수함"
    행들 = 처리(입력, rules.공사정보_읽기())
    저장(행들)
    print(f"DB 하자대장에 저장 완료 ({len(행들)}건)")
