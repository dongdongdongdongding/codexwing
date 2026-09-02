import { C } from "../theme";

/** 불러오기 실패를 화면에 말한다. 조용히 빈 박스로 두지 않는다. */
export function LoadFail({ err, what }: { err: string; what?: string }) {
  return (
    <div style={{
      background: `${C.down}14`, border: `1px solid ${C.down}44`, borderRadius: 12,
      padding: "14px 16px", color: C.down, fontSize: 13,
    }}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>✗ {what || "데이터"}를 불러오지 못했다</div>
      <div style={{ color: C.mut, fontFamily: "ui-monospace, monospace", fontSize: 12 }}>{err}</div>
    </div>
  );
}
