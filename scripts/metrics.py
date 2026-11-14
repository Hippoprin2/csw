#!/usr/bin/env python3
"""CSW 사용 지표 실행 스크립트.

scripts/metrics.sql 을 실제 DB에 실행하고 결과를 표로 출력한다.
DB 접속 정보는 .env.local 의 SUPABASE_DB_PASSWORD 를 사용한다 (값은 출력하지 않음).

접속 경로:
  1) db.<ref>.supabase.co:5432 (direct, IPv6/VPN 환경에서만 보통 resolve됨)
  2) aws-0-ap-northeast-1.pooler.supabase.com:5432 (session pooler, user=postgres.<ref>) ← 보통 이게 성공
  둘 다 psql 없이 psycopg2 로 접속한다 (pip install psycopg2-binary 필요).

실행:
  cd ~/projects/csw && python3 scripts/metrics.py
"""
import pathlib
import re
import sys

try:
    import psycopg2
except ImportError:
    sys.exit("psycopg2 가 설치되어 있지 않습니다: pip3 install psycopg2-binary")

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_REF = "xbifxrvgdimwwijijthl"


def _env(key: str) -> str:
    text = (ROOT / ".env.local").read_text()
    m = re.search(rf"^\s*{key}\s*=\s*(\S+)", text, re.M)
    if not m:
        raise RuntimeError(f"{key} not found in .env.local")
    return m.group(1)


def connect():
    pw = _env("SUPABASE_DB_PASSWORD")
    candidates = [
        dict(host=f"db.{PROJECT_REF}.supabase.co", port=5432, user="postgres"),
        dict(host="aws-0-ap-northeast-1.pooler.supabase.com", port=5432, user=f"postgres.{PROJECT_REF}"),
        dict(host="aws-0-ap-northeast-2.pooler.supabase.com", port=5432, user=f"postgres.{PROJECT_REF}"),
    ]
    last_err = None
    for c in candidates:
        try:
            conn = psycopg2.connect(dbname="postgres", password=pw, connect_timeout=8, **c)
            return conn
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"모든 접속 경로 실패: {last_err}")


def main():
    sql = (ROOT / "scripts" / "metrics.sql").read_text()
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        headers = ["metric", "key", "value"]
        widths = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(3)]
        def fmt(row):
            return "  ".join(str(row[i]).ljust(widths[i]) for i in range(3))
        print(fmt(headers))
        print("-" * (sum(widths) + 4))
        for r in rows:
            print(fmt(r))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
