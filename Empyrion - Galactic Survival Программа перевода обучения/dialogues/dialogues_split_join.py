from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


SOURCE_CSV = Path("Dialogues.csv")
OUTPUT_CSV = Path("Dialogues_russian.csv")
PART_PREFIX = "Dialogues_russian_part_"
BLOCKS_PER_FILE = 120

KEY_RE = re.compile(r"^<<<KEY:(dialogue_[^>\r\n]+)>>>\r?\n?", re.MULTILINE)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("CSV пустой или не содержит заголовка.")
                rows = list(reader)
                return reader.fieldnames, rows
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Не удалось прочитать {path} как UTF-8.")


def validate_columns(headers: list[str]) -> None:
    required = {"KEY", "English", "Russian"}
    missing = required - set(headers)

    if missing:
        raise ValueError(
            "В CSV не найдены обязательные столбцы: "
            + ", ".join(sorted(missing))
        )


def get_source() -> tuple[list[str], list[dict[str, str]]]:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Не найден исходный файл: {SOURCE_CSV}")

    headers, rows = read_csv(SOURCE_CSV)
    validate_columns(headers)

    bad_rows = [
        str(index + 2)
        for index, row in enumerate(rows)
        if not (row.get("KEY") or "").startswith("dialogue_")
    ]

    if bad_rows:
        preview = ", ".join(bad_rows[:10])
        raise ValueError(
            "Найдены строки без ключа dialogue_ в столбце KEY. "
            f"Номера строк CSV: {preview}"
        )

    keys = [row["KEY"] for row in rows]

    if len(keys) != len(set(keys)):
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        raise ValueError(
            "В исходном CSV есть повторяющиеся ключи. Например: "
            + ", ".join(duplicates[:10])
        )

    return headers, rows


def block(key: str, text: str) -> str:
    return f"<<<KEY:{key}>>>\n{text}\n\n"


def split_files() -> None:
    _, rows = get_source()

    old_parts = sorted(Path(".").glob(f"{PART_PREFIX}*.txt"))
    if old_parts:
        print("Внимание: существующие части будут перезаписаны:")
        for path in old_parts:
            print(f"  {path.name}")

    parts_created = 0

    for start in range(0, len(rows), BLOCKS_PER_FILE):
        chunk = rows[start:start + BLOCKS_PER_FILE]
        part_number = start // BLOCKS_PER_FILE + 1
        path = Path(f"{PART_PREFIX}{part_number:02d}.txt")

        content = "".join(
            block(row["KEY"], row.get("English", ""))
            for row in chunk
        )

        path.write_text(content, encoding="utf-8", newline="\n")
        parts_created += 1
        print(f"Создан: {path.name} | блоков: {len(chunk)}")

    print(f"\nГотово. Частей создано: {parts_created}.")
    print("Переводите только текст после <<<KEY:...>>>.")
    print("Ключи, теги, @q0/@d1/@w1, \\n и {PlayerName} не меняйте.")


def read_parts() -> dict[str, str]:
    part_paths = sorted(
        Path(".").glob(f"{PART_PREFIX}*.txt"),
        key=lambda p: p.name.lower()
    )

    if not part_paths:
        raise FileNotFoundError(
            f"Не найдены части вида {PART_PREFIX}XX.txt. "
            "Сначала выполните split."
        )

    translations: dict[str, str] = {}
    duplicate_keys: list[str] = []

    for path in part_paths:
        text = path.read_text(encoding="utf-8-sig")
        matches = list(KEY_RE.finditer(text))

        if not matches:
            raise ValueError(
                f"В файле {path.name} не найдено ни одного блока <<<KEY:dialogue_...>>>."
            )

        count = 0

        for index, match in enumerate(matches):
            key = match.group(1)
            text_start = match.end()
            text_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

            translation = text[text_start:text_end]
            translation = translation.rstrip("\r\n")

            if key in translations:
                duplicate_keys.append(key)
            else:
                translations[key] = translation

            count += 1

        print(f"Прочитан: {path.name} | блоков: {count}")

    if duplicate_keys:
        preview = ", ".join(sorted(set(duplicate_keys))[:10])
        raise ValueError(
            f"Повторяющиеся ключи в частях: {len(set(duplicate_keys))}. "
            f"Например: {preview}"
        )

    return translations


def join_files() -> None:
    headers, rows = get_source()
    translations = read_parts()

    source_keys = [row["KEY"] for row in rows]
    source_set = set(source_keys)
    translated_set = set(translations)

    missing = [key for key in source_keys if key not in translated_set]
    extra = sorted(translated_set - source_set)

    if missing:
        preview = ", ".join(missing[:10])
        raise ValueError(
            f"Не хватает ключей: {len(missing)}. Например: {preview}"
        )

    if extra:
        preview = ", ".join(extra[:10])
        raise ValueError(
            f"Найдены лишние ключи: {len(extra)}. Например: {preview}"
        )

    empty = [key for key in source_keys if not translations[key].strip()]

    if empty:
        preview = ", ".join(empty[:10])
        raise ValueError(
            f"Пустой перевод у ключей: {len(empty)}. Например: {preview}"
        )

    for row in rows:
        row["Russian"] = translations[row["KEY"]]

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=headers,
            extrasaction="raise",
            lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nГотово: {OUTPUT_CSV}")
    print(f"Записей в Russian: {len(rows)}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"split", "join"}:
        print("Использование:")
        print("  py dialogues_split_join.py split")
        print("  py dialogues_split_join.py join")
        raise SystemExit(2)

    if sys.argv[1] == "split":
        split_files()
    else:
        join_files()


if __name__ == "__main__":
    main()