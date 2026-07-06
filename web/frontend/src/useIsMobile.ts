import { useEffect, useState } from "react";

export function useIsMobile(bp = 768) {
  const [m, setM] = useState(() => typeof window !== "undefined" && window.matchMedia(`(max-width:${bp}px)`).matches);
  useEffect(() => {
    const q = window.matchMedia(`(max-width:${bp}px)`);
    const fn = (e: MediaQueryListEvent) => setM(e.matches);
    q.addEventListener("change", fn);
    return () => q.removeEventListener("change", fn);
  }, [bp]);
  return m;
}
