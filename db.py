"""저장은 이 파일에서만 한다. 연결 정보(DATABASE_URL)는 .env에서 읽고 화면에 출력하지 않는다.

처음 연결할 때 테이블 2개(접수, 하자대장)를 만들고 둘 다 RLS를 켠다.
RLS 정책은 만들지 않으므로 Supabase의 공개 API(anon·authenticated)로는 읽고 쓸 수 없고,
이 연결(테이블 소유자)만 쓸 수 있다.
"""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).parent / ".env")

대장_칸 = [
    "접수번호", "접수일", "원문파일", "위치", "공종", "하자내용", "긴급도", "조치기한",
    "공사번호", "시공업체", "준공일", "보증만료일", "보증판정", "책임구분", "상태", "비고",
]
날짜_칸 = ["접수일", "조치기한", "준공일", "보증만료일"]  # 나머지는 글

_테이블_만들기 = [
    """CREATE TABLE IF NOT EXISTS "접수" (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        "접수일시" TIMESTAMPTZ NOT NULL DEFAULT now(),
        "발견일" DATE,
        "접수자" TEXT,
        "부서" TEXT,
        "위치" TEXT,
        "내용" TEXT,
        "처리상태" TEXT NOT NULL DEFAULT '미처리' CHECK ("처리상태" IN ('미처리', '처리완료')),
        "접수번호" TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS "하자대장" (
        "접수번호" TEXT PRIMARY KEY,
        "접수일" DATE, "원문파일" TEXT, "위치" TEXT, "공종" TEXT, "하자내용" TEXT,
        "긴급도" TEXT, "조치기한" DATE, "공사번호" TEXT, "시공업체" TEXT,
        "준공일" DATE, "보증만료일" DATE, "보증판정" TEXT, "책임구분" TEXT,
        "상태" TEXT, "비고" TEXT
    )""",
    'ALTER TABLE "접수" ENABLE ROW LEVEL SECURITY',
    'ALTER TABLE "하자대장" ENABLE ROW LEVEL SECURITY',
]

_엔진 = None


def 엔진():
    """연결은 한 번만 만들고, 처음 만들 때 테이블과 RLS를 준비한다."""
    global _엔진
    if _엔진 is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError(".env에 DATABASE_URL이 없습니다.")
        for 앞 in ("postgres://", "postgresql://"):
            if url.startswith(앞):
                url = "postgresql+psycopg://" + url[len(앞):]
        엔진_ = create_engine(url, pool_pre_ping=True)
        with 엔진_.begin() as conn:
            for sql in _테이블_만들기:
                conn.execute(text(sql))
        _엔진 = 엔진_
    return _엔진


def _값(칸, 값):
    """CSV·화면의 글을 DB 값으로. 날짜 칸의 빈 글은 비어 있는 값(NULL)으로 둔다."""
    if 칸 in 날짜_칸:
        return date.fromisoformat(값) if 값 else None
    return 값


def 대장_저장(행들):
    """하자대장에 저장한다. 같은 접수번호가 있으면 그 행을 덮어쓴다."""
    칸들 = ", ".join(f'"{c}"' for c in 대장_칸)
    자리 = ", ".join(f":c{i}" for i in range(len(대장_칸)))
    갱신 = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in 대장_칸[1:])
    sql = text(f'INSERT INTO "하자대장" ({칸들}) VALUES ({자리}) ON CONFLICT ("접수번호") DO UPDATE SET {갱신}')
    값들 = [{f"c{i}": _값(c, 행.get(c, "")) for i, c in enumerate(대장_칸)} for 행 in 행들]
    if 값들:
        with 엔진().begin() as conn:
            conn.execute(sql, 값들)


def 대장_읽기():
    """하자대장 전체를 접수번호 순으로 읽는다. 날짜는 'YYYY-MM-DD' 글, 빈 값은 ''."""
    칸들 = ", ".join(f'"{c}"' for c in 대장_칸)
    with 엔진().connect() as conn:
        rows = conn.execute(text(f'SELECT {칸들} FROM "하자대장" ORDER BY "접수번호"')).mappings().all()
    return [
        {c: ("" if r[c] is None else r[c].isoformat() if c in 날짜_칸 else r[c]) for c in 대장_칸}
        for r in rows
    ]


def 건수():
    """테이블별 건수 {'접수': n, '하자대장': n}"""
    with 엔진().connect() as conn:
        return {t: conn.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in ("접수", "하자대장")}
