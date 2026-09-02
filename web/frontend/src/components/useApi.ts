import { useEffect, useState } from "react";

/** API 호출 1건 — 데이터·오류·로딩을 함께 낸다.
 *
 * 왜: 페이지 13곳이 `.catch(() => {})` 로 오류를 삼키고 있었다. API 가 하나라도 죽으면
 * 그 화면은 **영원히 빈 회색 박스**가 되고 이유가 어디에도 안 뜬다.
 * 실제로 2026-09-02 검증 때 조정관이 그 모양을 보고 「페이지 4개가 깨졌다」고 오진했다
 * (실은 로딩 중이었다) — 로딩과 실패가 화면에서 구분되지 않는다는 것이 그 증거다.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr("");
    fetcher()
      .then((d) => { if (alive) { setData(d); setLoading(false); } })
      .catch((e) => {
        if (!alive) return;
        setErr(e?.message || String(e) || "불러오지 못했다");
        setLoading(false);
      });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, err, loading };
}
