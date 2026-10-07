from pathlib import Path
import csv
import shutil
import sys
from datetime import datetime

PDA_FILE = Path(__file__).with_name("PDA.csv")
TRANSLATION_FILE = Path(__file__).with_name("PDA_english_to_russian.csv")


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError(f"Не удалось прочитать заголовки: {path.name}")

        rows = list(reader)
        return reader.fieldnames, rows


def export_english():
    fields, rows = read_csv(PDA_FILE)

    if "KEY" not in fields or "English" not in fields:
        raise ValueError("В PDA.csv должны быть колонки KEY и English.")

    result = []

    for row in rows:
        key = row.get("KEY", "").strip()
        english = row.get("English", "")

        if key and english.strip():
            result.append({
                "KEY": key,
                "English": english,
                "Russian": ""
            })

    with TRANSLATION_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["KEY", "English", "Russian"],
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(result)

    print(f"Экспортировано строк: {len(result)}")
    print(f"Файл для перевода: {TRANSLATION_FILE}")


def import_russian():
    if not TRANSLATION_FILE.exists():
        raise FileNotFoundError(
            f"Не найден файл перевода: {TRANSLATION_FILE.name}"
        )

    fields, pda_rows = read_csv(PDA_FILE)

    if "KEY" not in fields or "Russian" not in fields:
        raise ValueError("В PDA.csv должны быть колонки KEY и Russian.")

    _, translation_rows = read_csv(TRANSLATION_FILE)

    translations = {}

    for row in translation_rows:
        key = row.get("KEY", "").strip()
        russian = row.get("Russian", "")

        if key and russian.strip():
            translations[key] = russian

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = PDA_FILE.with_name(f"PDA.csv.backup_{stamp}")
    shutil.copy2(PDA_FILE, backup)

    updated = 0

    for row in pda_rows:
        key = row.get("KEY", "").strip()

        if key in translations:
            new_text = translations[key]

            if row.get("Russian", "") != new_text:
                row["Russian"] = new_text
                updated += 1

    output = PDA_FILE.with_name("PDA.csv")

    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(pda_rows)

    print(f"Переводов импортировано: {len(translations)}")
    print(f"Строк обновлено: {updated}")
    print(f"Резервная копия: {backup.name}")
    print(f"Новый PDA-файл: {output.name}")
    print("Проверь PDA.csv.new, затем замени им PDA.csv.")


def usage():
    print("Использование:")
    print("  py pda_translate.py export")
    print("  py pda_translate.py import")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
        raise SystemExit(1)

    command = sys.argv[1].lower()

    if command == "export":
        export_english()
    elif command == "import":
        import_russian()
    else:
        usage()
        raise SystemExit(1)