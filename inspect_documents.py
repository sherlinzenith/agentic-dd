from pathlib import Path

for file in sorted(Path("documents").glob("*.txt")):

    print("\n" + "=" * 70)
    print(file.name)
    print("=" * 70)

    text = file.read_text(encoding="utf-8")

    for i, line in enumerate(text.splitlines(), start=1):
        print(f"{i}: {repr(line)}")
