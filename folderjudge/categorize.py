"""Extension -> life-form classification."""
from __future__ import annotations

JUNK_EXTS = {
    ".crdownload",   # Chrome partial
    ".download",     # Firefox partial
    ".opdownload",   # Opera partial
    ".part",         # Firefox/Edge partial
    ".partial",      # misc partial
    ".tmp",
    ".temp",
    ".!ut",          # uTorrent partial
    ".ytdl",         # yt-dlp temp
    ".listing",
}

INSTALLER_EXTS = {
    ".exe", ".msi", ".msix", ".msixbundle", ".deb", ".rpm",
    ".pkg", ".dmg", ".appimage", ".apk", ".appx",
}

_OTHER: dict[str, str] = {}


def _exts(cats: dict[str, str]) -> None:
    for cat, exts in cats.items():
        for e in exts.split():
            _OTHER[e] = cat


_exts({
    "archive": ".zip .7z .rar .tar .gz .tgz .bz2 .xz .zst .cab .lz .lz4",
    "disc":    ".iso .img .vhd .vhdx .mds .mdf",
    "document": ".pdf .doc .docx .odt .rtf .txt .md .pages .tex .ps",
    "ebook":   ".epub .mobi .azw3 .fb2 .djvu",
    "sheet":   ".xls .xlsx .ods .csv .tsv .num",
    "slides":  ".ppt .pptx .odp .key",
    "image":   ".png .jpg .jpeg .gif .webp .bmp .svg .heic .heif .avif .tiff .ico .psd .xd",
    "video":   ".mp4 .mkv .webm .mov .avi .flv .wmv .m4v .mpg .ts .3gp",
    "audio":   ".mp3 .flac .wav .ogg .oga .opus .m4a .wma .mid .aiff",
    "code":    ".py .js .mjs .ts .tsx .sh .bash .zsh .json .xml .yml .yaml .toml .html .htm "
               ".css .scss .c .h .cpp .hpp .rs .go .java .kt .swift .lua .pl .rb .sql "
               ".ipynb .jar .bat .ps1",
    "font":    ".ttf .otf .woff .woff2 .ttc",
    "torrent": ".torrent",
    "model":   ".gguf .safetensors .onnx .pth .pt .ckpt .bin",
    "binary":  ".so .dll .dylib .o .a .el .deb-tmp",
})

JUNK = "junk"
INSTALLER = "installer"
OTHER = "other"


def categorize(ext: str) -> str:
    ext = ext.lower()
    if ext in JUNK_EXTS:
        return JUNK
    if ext in INSTALLER_EXTS:
        return INSTALLER
    return _OTHER.get(ext, OTHER)


def emoji_for(cat: str) -> str:
    return {
        JUNK: "🧟", INSTALLER: "📦", "archive": "🗄️", "disc": "💿",
        "document": "📄", "ebook": "📚", "sheet": "📊", "slides": "📽️",
        "image": "🖼️", "video": "🎬", "audio": "🎵", "code": "🧑‍💻",
        "font": "🔤", "torrent": "🧲", "model": "🧠", "binary": "⚙️",
        OTHER: "❓",
    }.get(cat, "❓")
