import { LaneStatus } from "../api";
import { C } from "../theme";

export function LaneRunStatus({ rows = [] }: { rows?: LaneStatus[] }) {
  if (!rows.length) return null;
  return <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
    {rows.map((row) => <div key={row.lane} style={{ padding: "10px 12px", borderRadius: 8,
      border: `1px solid ${C.line}`, background: C.surface, fontSize: 12 }}>
      <b>{row.label}</b><span style={{ color: C.mut }}> · {row.as_of || "실행일 확인 불가"}
        {row.scored_rows != null && ` · ${row.scored_rows}종목 계산`}</span>
      <div style={{ marginTop: 4, color: ["error", "stale", "blocked"].includes(row.status) ? C.warn : C.mut }}>
        {row.reason}
      </div>
    </div>)}
  </div>;
}
