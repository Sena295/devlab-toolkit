"""Classification rules: map a file to a destination category."""
from __future__ import annotations

from pathlib import Path

CATEGORIES: dict[str, set[str]] = {
    "Imagens": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"},
    "Documentos": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md"},
    "Planilhas": {".xls", ".xlsx", ".csv", ".ods"},
    "Apresentacoes": {".ppt", ".pptx", ".odp", ".key"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg"},
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Compactados": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Codigo": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".sql", ".sh"},
    "Executaveis": {".exe", ".msi", ".dmg", ".deb", ".apk"},
}
FALLBACK = "Outros"

_EXT_TO_CATEGORY = {ext: cat for cat, exts in CATEGORIES.items() for ext in exts}


def classify(path: Path) -> str:
    return _EXT_TO_CATEGORY.get(path.suffix.lower(), FALLBACK)


def parse_custom_rules(pairs: list[str]) -> dict[str, str]:
    """Parse ``.ext=Folder`` overrides given on the command line."""
    rules = {}
    for pair in pairs:
        ext, sep, folder = pair.partition("=")
        if not sep or not folder or not ext.startswith("."):
            raise ValueError(f"regra inválida '{pair}' (use .ext=Pasta)")
        rules[ext.lower()] = folder
    return rules
