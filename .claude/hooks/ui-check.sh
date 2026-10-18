#!/usr/bin/env bash
# PostToolUse-хук: после правок в src/main/resources/static/ запускает UI-тесты —
# скриншотные (внешний вид) и e2e (поведение сценариев cards-web-ui).
# Код 2 передаёт stderr Claude как обратную связь (см. раздел «Тестирование» в CLAUDE.md).
set -uo pipefail

file_path=$(jq -r '.tool_input.file_path // empty')
project_dir=${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}

case "$file_path" in
  "$project_dir"/src/main/resources/static/* | src/main/resources/static/*) ;;
  *) exit 0 ;;
esac

cd "$project_dir" || exit 0
# --continue: при падении одного набора всё равно прогнать второй и показать оба результата.
if output=$(./gradlew screenshotTest e2eTest --continue -q --console=plain 2>&1); then
  exit 0
fi

{
  echo "UI-тесты не прошли после правки $file_path."
  echo "Упавшие тесты:"
  grep -E '✘' <<<"$output" | sed 's/^ */  /'
  if grep -qE '✘.* tests/' <<<"$output"; then
    echo "Скриншоты: $project_dir/ui-tests/test-results/ (*-diff.png). Если изменение вида не было целью задачи — исправьте код;"
    echo "  если было — покажите пользователю diff и обновите эталоны (./gradlew screenshotUpdate) только после его подтверждения."
  fi
  if grep -qE '✘.* e2e/' <<<"$output"; then
    echo "E2E: нарушено поведение сценария cards-web-ui — исправьте код (трейсы: $project_dir/ui-tests/test-results-e2e/)."
  fi
} >&2
exit 2
