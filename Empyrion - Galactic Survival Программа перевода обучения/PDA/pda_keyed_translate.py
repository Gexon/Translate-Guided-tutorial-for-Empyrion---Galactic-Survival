from pathlib import Path
import csv
import shutil
import sys
import re
from datetime import datetime

CSV_FILE = Path(__file__).with_name("PDA_english_to_russian.csv")
ENGLISH_FILE = Path(__file__).with_name("PDA_english_keyed.txt")
RUSSIAN_FILE = Path(__file__).with_name("PDA_russian_keyed.txt")

KEY_PATTERN = re.compile(r"^<<<KEY:([^>\r\n]+)>>>$", re.MULTILINE)


def read_csv():
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError("Не удалось прочитать заголовки CSV.")

        required = {"KEY", "English", "Russian"}
        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                "Нет обязательных колонок: " + ", ".join(sorted(missing))
            )

        return reader.fieldnames, list(reader)


def export_text():
    _, rows = read_csv()

    with ENGLISH_FILE.open("w", encoding="utf-8") as f:
        for index, row in enumerate(rows):
            key = row.get("KEY", "").strip()
            english = row.get("English", "")

            if not key:
                continue

            f.write(f"<<<KEY:{key}>>>\n")
            f.write(english.rstrip("\r\n"))
            f.write("\n")

            if index != len(rows) - 1:
                f.write("\n")

    print(f"Экспортировано записей: {len(rows)}")
    print(f"Файл английского текста: {ENGLISH_FILE.name}")
    print()
    print("Скопируй его как PDA_russian_keyed.txt.")
    print("Переводи только текст под <<<KEY:...>>>.")
    print("Не изменяй и не удаляй строки <<<KEY:...>>>.")


def parse_keyed_text(text: str) -> dict:
    matches = list(KEY_PATTERN.finditer(text))

    if not matches:
        raise ValueError(
            "Не найдены ключи формата <<<KEY:ключ>>>."
        )

    translations = {}

    for index, match in enumerate(matches):
        key = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        value = text[start:end]

        # Убираем только разделительные переносы между блоками.
        value = value.lstrip("\r\n")
        value = value.rstrip("\r\n")

        if key in translations:
            raise ValueError(f"Повторяющийся ключ в файле перевода: {key}")

        translations[key] = value

    return translations


def import_text():
    if not RUSSIAN_FILE.exists():
        raise FileNotFoundError(
            f"Нет файла перевода: {RUSSIAN_FILE.name}"
        )

    fields, rows = read_csv()

    russian_text = RUSSIAN_FILE.read_text(encoding="utf-8-sig")
    translations = parse_keyed_text(russian_text)

    csv_keys = {
        row.get("KEY", "").strip()
        for row in rows
        if row.get("KEY", "").strip()
    }

    unknown_keys = set(translations) - csv_keys

    if unknown_keys:
        example = ", ".join(sorted(unknown_keys)[:5])
        raise ValueError(
            "В файле перевода есть ключи, которых нет в CSV: " + example
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = CSV_FILE.with_name(
        f"PDA_english_to_russian.backup_{stamp}.csv"
    )
    shutil.copy2(CSV_FILE, backup)

    updated = 0
    skipped_empty = 0

    for row in rows:
        key = row.get("KEY", "").strip()

        if key not in translations:
            continue

        russian = translations[key]

        if not russian.strip():
            skipped_empty += 1
            continue

        if row.get("Russian", "") != russian:
            row["Russian"] = russian
            updated += 1

    output = CSV_FILE.with_name("PDA_english_to_russian.csv")

    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Ключей в переводе: {len(translations)}")
    print(f"Строк обновлено: {updated}")
    print(f"Пустых переводов пропущено: {skipped_empty}")
    print(f"Резервная копия: {backup.name}")
    print(f"Готовый CSV: {output.name}")
    print("Проверь новый CSV, затем замени исходный файл.")


def usage():
    print("Использование:")
    print("  py pda_keyed_translate.py export")
    print("  py pda_keyed_translate.py import")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
        raise SystemExit(1)

    command = sys.argv[1].lower()

    if command == "export":
        export_text()
    elif command == "import":
        import_text()
    else:
        usage()
        raise SystemExit(1)