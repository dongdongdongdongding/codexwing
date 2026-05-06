---
name: issue
description: Beads 이슈 상태 관리. Claude /issue와 같은 start, done/end, sync, log 흐름을 Codex에서 실행한다.
argument-hint: "[start|done|end|sync|log] [issue-id] [reason]"
allowed-tools: Bash
---

이 프로젝트의 Beads 이슈 상태를 관리한다. Claude의 `/issue` 워크플로와 동일한 공통 래퍼를 사용한다.

인자: $ARGUMENTS

---

## 실행

항상 저장소 루트에서 아래 명령을 사용한다:

```bash
scripts/issue $ARGUMENTS
```

## 동작

- 인자 없음: `bd status`, in_progress, ready 상위 5개를 요약한다.
- `start [issue-id]`: 이슈를 claim하고 `bd show`를 출력한다. id가 없으면 ready 목록 중 P1 첫 번째, 없으면 첫 번째 ready 이슈를 선택한다.
- `done|end <issue-id> [reason]`: 이슈를 닫는다. reason이 없으면 최근 git commit 제목을 사용한다.
- `sync`: `bd sync`를 실행한다.
- `log`: 최근 closed 이슈 5개를 출력한다.

Codex가 직접 slash command를 받지 못하는 환경에서는 사용자가 `/issue start ...`라고 말하면 같은 의미로 `scripts/issue start ...`를 실행한다.
