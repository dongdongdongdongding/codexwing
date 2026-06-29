/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 운영 백엔드 베이스 URL (로컬 백엔드 터널 주소). 미설정시 같은 오리진 /api. */
  readonly VITE_API_BASE?: string;
  /** 백엔드 WEB_API_TOKEN과 일치하는 경량 접근 토큰. */
  readonly VITE_API_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
