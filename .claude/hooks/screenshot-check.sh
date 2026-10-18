#!/usr/bin/env bash
# PostToolUse-хук: после правок в src/main/resources/static/ сравнивает скриншоты интерфейса с эталонами.
# Код 2 передаёт stderr Claude как обратную связь (см. раздел «Скриншотные тесты» в CLAUDE.md).
set -uo pipefail

file_path=$(jq -r '.tool_input.file_path // empty')
project_dir=${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}

case "$file_path" in
  "$project_dir"/src/main/resources/static/* | src/main/resources/static/*) ;;
  *) exit 0 ;;
esac

cd "$project_dir" || exit 0
if output=$(./gradlew screenshotTest -q --console=plain 2>&1); then
  exit 0
fi

{
  echo "Скриншотные тесты интерфейса не прошли после правки $file_path."
  echo "Упавшие тесты:"
  grep -E '✘' <<<"$output" | sed 's/^ */  /'
  echo "Diff-изображения: $project_dir/ui-tests/test-results/ (файлы *-diff.png)"
  echo "Если изменение внешнего вида не было целью задачи — исправьте код."
  echo "Если было — покажите пользователю diff и обновите эталоны (./gradlew screenshotUpdate) только после его подтверждения."
} >&2
exit 2
