---
name: issue
description: Beads 이슈 상태 관리. 작업 시작(start), 완료(done/end), 상태 확인(기본), 동기화(sync), 이력(log)
argument-hint: "[start|done|end|sync|log] [issue-id] [reason]"
allowed-tools: Bash
---

이 프로젝트의 Beads 이슈 상태를 관리한다. Codex와 공유하는 `scripts/issue` 래퍼를 실행한다.

인자: $ARGUMENTS

---

## 실행

Bash 도구로 저장소 루트에서 아래 명령을 실행한다:

```bash
scripts/issue $ARGUMENTS
```

---

## 인자별 동작

### 인자 없음
현재 상태를 사람이 읽기 좋게 요약해서 보여준다:
- 진행 중인 이슈 목록 (없으면 "없음")
- 지금 시작 가능한 이슈 (우선순위 순 상위 5개)
- 안내: "시작: `/issue start <id>` | 완료: `/issue end <id>`"

### `start` (예: `/issue start` 또는 `/issue start swing-main-ofk`)
- id가 없으면: ready 목록 중 P1 첫 번째 이슈를 자동 선택
- `scripts/issue start <id>` 실행
- 완료 후 `bd show <id>` 로 작업 내용 출력

### `done` 또는 `end`
- `/issue done ...` 과 `/issue end ...` 는 같은 종료 동작이다

예:
- `/issue done swing-main-ofk`
- `/issue end swing-main-ofk`
- `/issue end swing-main-ofk "수식 수정 완료"`

- id가 없으면: in_progress 목록 보여주고 어떤 것을 닫을지 물어본다
- reason이 없으면: `git log -1 --pretty=%s` 로 최근 커밋 메시지를 reason으로 사용
- `scripts/issue end <id> "<reason>"` 실행
- 완료 후 새로 unblock된 이슈가 있으면 안내

### `sync`
`scripts/issue sync` 실행 후 결과 출력

### `log`
`scripts/issue log` 실행 후 최근 완료된 이슈 5개를 날짜와 함께 출력
