# NCERT Book Browser

A simple terminal utility to browse and view NCERT textbook chapters directly in your browser - no downloading required!

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Browse by Class** - Navigate through Classes 1-12
- **Search** - Find books by title or subject
- **View Chapters** - See all available chapters for a book
- **Open in Browser** - View chapters directly without downloading
- **Download** - Download individual chapters if needed
- **No Account Required** - Works with the public NCERT website

## Installation

### Quick Start

```bash
cd ncert-fetcher
./run.sh
```

### Manual Installation

```bash
pip install -r requirements.txt
python ncert_browser.py
```

## Usage

### Interactive Mode

Simply run without arguments:

```bash
python ncert_browser.py
# or
./run.sh
```

You'll see a menu with options to:
1. Browse by class
2. Search for a book
3. View book chapters
4. Download a chapter
5. Update catalog

### Command Line Options

**List all books:**
```bash
python ncert_browser.py --list
```

**Search for a book:**
```bash
python ncert_browser.py --search "physics"
python ncert_browser.py --search "mathematics"
```

**List books for a class:**
```bash
python ncert_browser.py --class 10
```

**View specific chapter:**
```bash
# View Class 10, Mathematics, book 1, chapter 5
python ncert_browser.py --view 10 mathematics 1 5
```

**Open chapter in browser:**
```bash
python ncert_browser.py --open 10 mathematics 1 5
```

**Get direct download URL:**
```bash
python ncert_browser.py --get 10 mathematics 1 5
```

**Download chapter:**
```bash
python ncert_browser.py --dl 10 mathematics 1 5
```

## How It Works

The tool uses the official NCERT textbook catalog and generates URLs for individual chapter PDFs:

```
https://ncert.nic.in/textbook/pdf/{book_code}{chapter_number:02d}.pdf
```

For example:
- Class 10 Mathematics Part 1, Chapter 5: `https://ncert.nic.in/textbook/pdf/jemh105.pdf`

## Dependencies

- **rich** - For beautiful terminal UI
- **requests** - For HTTP requests

## Disclaimer

This tool is for educational purposes only. NCERT textbooks are copyrighted material provided free by NCERT for educational use.

## License

MIT License
