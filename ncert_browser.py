#!/usr/bin/env python3
"""
NCERT Book Browser - Simple terminal utility to browse NCERT textbook chapters
No downloading needed - view chapters directly in your browser or download individual ones
"""

import argparse
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

import requests
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box

console = Console()

BASE_URL = "https://ncert.nic.in/textbook/pdf/"
DATA_URL = "https://raw.githubusercontent.com/aayushdutt/ncert-downloader/main/data.json"
TEXTBOOK_URL = "https://ncert.nic.in/textbook.php"


def get_data_file():
    return Path.home() / ".ncert-fetcher" / "data.json"


def fetch_catalog(force=False):
    data_file = get_data_file()
    data_file.parent.mkdir(parents=True, exist_ok=True)

    if not force and data_file.exists():
        with open(data_file) as f:
            return json.load(f)

    console.print("[cyan]Fetching latest book catalog...[/cyan]")
    try:
        response = requests.get(DATA_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        with open(data_file, "w") as f:
            json.dump(data, f)
        return data
    except Exception as e:
        if data_file.exists():
            with open(data_file) as f:
                return json.load(f)
        console.print(f"[red]Failed to fetch catalog: {e}[/red]")
        sys.exit(1)


def get_chapter_urls(book_code, num_chapters):
    """Generate list of chapter PDF URLs"""
    urls = []
    for i in range(num_chapters + 1):
        url = f"{BASE_URL}{book_code}{i:02d}.pdf"
        urls.append((i, url))
    return urls


def check_chapter_exists(url):
    """Check if a chapter PDF exists (HEAD request)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.head(url, timeout=10, headers=headers, allow_redirects=True)
        if response.status_code == 200:
            size = int(response.headers.get("Content-Length", 0))
            return True, size
        return False, 0
    except:
        return False, 0


def list_chapters(book_code, book_title, chapters_range):
    """List all available chapters for a book"""
    start, end = map(int, chapters_range.split("-"))

    console.print(f"\n[bold cyan]Book:[/bold cyan] {book_title}")
    console.print(f"[bold cyan]Code:[/bold cyan] {book_code}")
    console.print(f"[bold cyan]Checking chapters...[/bold cyan]\n")

    table = Table(title=f"[bold]Available Chapters[/bold]", box=box.ROUNDED)
    table.add_column("Chapter", style="cyan", justify="center", width=10)
    table.add_column("URL", style="dim", width=50)
    table.add_column("Status", style="green", width=10)
    table.add_column("Size", width=12)

    available = []
    for i in range(start, end + 1):
        url = f"{BASE_URL}{book_code}{i:02d}.pdf"
        exists, size = check_chapter_exists(url)
        if exists:
            size_str = (
                f"{size / (1024 * 1024):.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
            )
            table.add_row(f"Chapter {i}", url, "[green]Available[/green]", size_str)
            available.append((i, url, size))
        else:
            table.add_row(f"Chapter {i}", url, "[dim]Not found[/dim]", "-")

    console.print(table)
    console.print(f"\n[dim]Found {len(available)} available chapter(s)[/dim]")
    return available


def view_chapter(url, browser=True):
    """Open chapter in browser or download"""
    if browser:
        console.print(f"[cyan]Opening in browser:[/cyan] {url}")
        webbrowser.open(url)
    else:
        console.print(f"[cyan]Download URL:[/cyan] {url}")


def open_in_browser(url):
    """Open URL in browser"""
    webbrowser.open(url)


def download_chapter(url, filename=None, output_dir=None):
    """Download a single chapter PDF"""
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if filename:
            dest = output_dir / filename
        else:
            dest = output_dir / url.split("/")[-1]
    else:
        dest = Path.home() / "Downloads" / (filename or url.split("/")[-1])
        dest.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Downloading:[/cyan] {url}")
    console.print(f"[cyan]To:[/cyan] {dest}")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, stream=True, timeout=60, headers=headers)
        response.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        size = dest.stat().st_size
        size_str = (
            f"{size / (1024 * 1024):.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        )
        console.print(f"[green]Downloaded! ({size_str})[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        return False


def search_books(data, query):
    """Search for books"""
    results = []
    query_lower = query.lower()

    for cls, subjects in data.items():
        for subject, books in subjects.items():
            for book in books:
                if book.get("code"):
                    if query_lower in subject.lower() or query_lower in book["text"].lower():
                        results.append(
                            {
                                "class": cls,
                                "subject": subject,
                                "title": book["text"],
                                "code": book["code"],
                                "chapters": book["chapters"],
                            }
                        )
    return results


def show_banner():
    banner = """
[bold cyan]╔═══════════════════════════════════════════════════════╗
║                                                               ║
║   [bold white]NCERT Book Browser[/bold white] - View Textbooks Online         ║
║                                                               ║
║   [dim]Browse and view NCERT chapters without downloading[/dim]  ║
║                                                               ║
╚═══════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner)


def interactive_mode(data):
    while True:
        show_banner()
        console.print("[bold]What would you like to do?[/bold]\n")
        console.print("  [cyan]1.[/cyan]  Browse by Class")
        console.print("  [cyan]2.[/cyan]  Search for a book")
        console.print("  [cyan]3.[/cyan]  View book chapters")
        console.print("  [cyan]4.[/cyan]  Download single chapter")
        console.print("  [cyan]5.[/cyan]  Update catalog")
        console.print("  [cyan]0.[/cyan]  Exit\n")

        choice = Prompt.ask("[bold cyan]Enter choice[/bold cyan]", default="0")

        if choice == "1":
            browse_by_class(data)
        elif choice == "2":
            search_mode(data)
        elif choice == "3":
            view_mode(data)
        elif choice == "4":
            download_mode(data)
        elif choice == "5":
            fetch_catalog(force=True)
            console.print("[green]Catalog updated![/green]")
        elif choice == "0":
            break


def browse_by_class(data):
    classes = sorted(data.keys(), key=int, reverse=True)

    console.print("\n[bold]Select a Class:[/bold]\n")
    for cls in classes:
        subjects = list(data[cls].keys())
        console.print(f"  [cyan]{cls:>2}.[/cyan]  Class {cls} ({len(subjects)} subjects)")

    console.print()
    choice = Prompt.ask("[bold cyan]Enter class number[/bold cyan]", default="10")

    if choice not in data:
        return

    cls = choice
    subjects = sorted(data[cls].keys())

    console.print(f"\n[bold]Class {cls} - Subjects:[/bold]\n")
    for i, subj in enumerate(subjects, 1):
        book_count = len([b for b in data[cls][subj] if b.get("code")])
        console.print(f"  [cyan]{i:>2}.[/cyan]  {subj} [dim]({book_count} books)[/dim]")

    console.print()
    subj_choice = Prompt.ask("[bold cyan]Enter subject number[/bold cyan]", default="1")

    try:
        subj_idx = int(subj_choice) - 1
        if 0 <= subj_idx < len(subjects):
            subj = subjects[subj_idx]
            books = [b for b in data[cls][subj] if b.get("code")]

            console.print(f"\n[bold]{subj} books:[/bold]\n")
            for i, book in enumerate(books, 1):
                console.print(f"  [cyan]{i:>2}.[/cyan]  {book['text']}")

            console.print()
            book_choice = Prompt.ask(
                "[bold cyan]Enter book number to view chapters[/bold cyan]", default="1"
            )

            try:
                book_idx = int(book_choice) - 1
                if 0 <= book_idx < len(books):
                    book = books[book_idx]
                    list_chapters(book["code"], book["text"], book["chapters"])

                    console.print()
                    if Confirm.ask("[cyan]Open in browser?[/cyan]", default=True):
                        url = f"{TEXTBOOK_URL}?{book['code']}={book['chapters']}"
                        open_in_browser(url)
            except ValueError:
                pass
    except ValueError:
        pass


def search_mode(data):
    console.print()
    query = Prompt.ask("[bold cyan]Search books[/bold cyan]")

    if not query.strip():
        return

    results = search_books(data, query)

    if not results:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return

    table = Table(title=f"[bold]Search Results for '{query}'[/bold]", box=box.ROUNDED)
    table.add_column("#", style="cyan", justify="center", width=4)
    table.add_column("Class", width=8)
    table.add_column("Subject", width=20)
    table.add_column("Book Title", width=40)

    for i, r in enumerate(results, 1):
        table.add_row(str(i), f"Class {r['class']}", r["subject"], r["title"])

    console.print()
    console.print(table)
    console.print()

    choice = Prompt.ask("[bold cyan]Enter book number to view[/bold cyan]", default="1")

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            r = results[idx]
            list_chapters(r["code"], r["title"], r["chapters"])

            console.print()
            if Confirm.ask("[cyan]Open in browser?[/cyan]", default=True):
                url = f"{TEXTBOOK_URL}?{r['code']}={r['chapters']}"
                open_in_browser(url)
    except ValueError:
        pass


def view_mode(data):
    """View chapters of a specific book"""
    console.print()

    # Get class
    classes = sorted(data.keys(), key=int, reverse=True)
    classes_str = ", ".join(classes)
    cls = Prompt.ask(f"[bold cyan]Enter class ({classes_str})[/bold cyan]", default="10")

    if cls not in data:
        console.print(f"[red]Invalid class: {cls}[/red]")
        return

    # Get subject
    subjects = sorted(data[cls].keys())
    console.print(f"\n[bold]Subjects:[/bold]")
    for i, subj in enumerate(subjects, 1):
        console.print(f"  {i}. {subj}")

    subj_idx = Prompt.ask("[bold cyan]Enter subject number[/bold cyan]", default="1")
    try:
        subj = subjects[int(subj_idx) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection[/red]")
        return

    # Get book
    books = [b for b in data[cls][subj] if b.get("code")]
    console.print(f"\n[bold]Books in {subj}:[/bold]")
    for i, book in enumerate(books, 1):
        console.print(f"  {i}. {book['text']}")

    book_idx = Prompt.ask("[bold cyan]Enter book number[/bold cyan]", default="1")
    try:
        book = books[int(book_idx) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection[/red]")
        return

    # List chapters
    available = list_chapters(book["code"], book["text"], book["chapters"])

    if not available:
        return

    console.print()
    chap_choice = Prompt.ask(
        "[bold cyan]Enter chapter number to open (or 'all' for all)[/bold cyan]", default="1"
    )

    if chap_choice.lower() == "all":
        for i, url, size in available:
            open_in_browser(url)
    else:
        try:
            chap_num = int(chap_choice)
            for i, url, size in available:
                if i == chap_num:
                    open_in_browser(url)
                    break
        except ValueError:
            pass


def download_mode(data):
    """Download a single chapter"""
    console.print()

    # Get class
    classes = sorted(data.keys(), key=int, reverse=True)
    cls = Prompt.ask(f"[bold cyan]Enter class[/bold cyan]", default="10")

    if cls not in data:
        console.print(f"[red]Invalid class: {cls}[/red]")
        return

    # Get subject
    subjects = sorted(data[cls].keys())
    console.print(f"\n[bold]Subjects:[/bold]")
    for i, subj in enumerate(subjects, 1):
        console.print(f"  {i}. {subj}")

    subj_idx = Prompt.ask("[bold cyan]Enter subject number[/bold cyan]", default="1")
    try:
        subj = subjects[int(subj_idx) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection[/red]")
        return

    # Get book
    books = [b for b in data[cls][subj] if b.get("code")]
    console.print(f"\n[bold]Books:[/bold]")
    for i, book in enumerate(books, 1):
        console.print(f"  {i}. {book['text']}")

    book_idx = Prompt.ask("[bold cyan]Enter book number[/bold cyan]", default="1")
    try:
        book = books[int(book_idx) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection[/red]")
        return

    # List and download chapter
    available = list_chapters(book["code"], book["text"], book["chapters"])

    if not available:
        return

    console.print()
    chap_choice = Prompt.ask("[bold cyan]Enter chapter number to download[/bold cyan]", default="1")

    try:
        chap_num = int(chap_choice)
        for i, url, size in available:
            if i == chap_num:
                filename = f"{book['text']}_Chapter_{i:02d}.pdf"
                download_chapter(url, filename)
                break
    except ValueError:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="NCERT Book Browser - View textbook chapters online",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ncert                     # Interactive mode
  ncert --list              # List all books
  ncert --search physics    # Search for books
  ncert --class 10         # List Class 10 books
  ncert --view 10 math 1   # View Class 10 Math book chapters
  ncert --open 10 math 1 3 # Open chapter 3 in browser
  ncert --get 10 math 1 3  # Get download URL for chapter 3
        """,
    )
    parser.add_argument("-l", "--list", action="store_true", help="List all books")
    parser.add_argument("-s", "--search", metavar="QUERY", help="Search for books")
    parser.add_argument("-c", "--class", dest="cls", metavar="N", help="Filter by class")
    parser.add_argument("--subject", metavar="NAME", help="Filter by subject")
    parser.add_argument(
        "--view",
        nargs=4,
        metavar=("CLASS", "SUBJECT", "BOOK_NUM", "CHAPTER"),
        help="View specific chapter: --view 10 Mathematics 1 3",
    )
    parser.add_argument(
        "--open",
        nargs=4,
        metavar=("CLASS", "SUBJECT", "BOOK_NUM", "CHAPTER"),
        help="Open chapter in browser: --open 10 Mathematics 1 3",
    )
    parser.add_argument(
        "--get",
        nargs=4,
        metavar=("CLASS", "SUBJECT", "BOOK_NUM", "CHAPTER"),
        help="Get chapter URL: --get 10 Mathematics 1 3",
    )
    parser.add_argument(
        "--dl",
        nargs=4,
        metavar=("CLASS", "SUBJECT", "BOOK_NUM", "CHAPTER"),
        help="Download chapter: --dl 10 Mathematics 1 3",
    )
    parser.add_argument("--update", action="store_true", help="Update catalog")

    args = parser.parse_args()

    data = fetch_catalog(force=args.update)

    if args.list:
        list_all_books(data, args.cls, args.subject)
        return

    if args.search:
        results = search_books(data, args.search)
        show_search_results(results, args.search)
        return

    if args.view or args.open or args.get or args.dl:
        cmd_args = args.view or args.open or args.get or args.dl
        cmd = "view" if args.view else "open" if args.open else "get" if args.get else "dl"
        handle_direct_command(data, cmd, cmd_args)
        return

    # Check if stdin has input (non-interactive)
    if not sys.stdin.isatty():
        console.print("[yellow]Non-interactive mode. Use --help for options.[/yellow]")
        return

    interactive_mode(data)


def list_all_books(data, cls_filter=None, subject_filter=None):
    classes = sorted(data.keys(), key=int)

    if cls_filter:
        classes = [c for c in classes if c == str(cls_filter)]

    table = Table(title="[bold]NCERT Books Catalog[/bold]", show_lines=True, box=box.ROUNDED)
    table.add_column("Class", style="cyan", justify="center", width=8)
    table.add_column("Subject", style="green", width=20)
    table.add_column("Books", style="white")

    seen = set()
    for cls in classes:
        subjects = data.get(cls, {})
        for subj, books in sorted(subjects.items()):
            if subject_filter and subject_filter.lower() not in subj.lower():
                continue
            if (cls, subj) not in seen:
                book_titles = [b["text"] for b in books if b.get("code")]
                seen.add((cls, subj))
                table.add_row(f"Class {cls}", subj, f"[dim]{len(book_titles)} book(s)[/dim]")

    console.print()
    console.print(table)
    console.print()


def show_search_results(results, query):
    if not results:
        console.print(f"\n[yellow]No results found for '{query}'[/yellow]")
        return

    table = Table(
        title=f"[bold]Search Results for '{query}'[/bold] ({len(results)} books)",
        show_lines=True,
        box=box.ROUNDED,
    )
    table.add_column("Class", style="cyan", justify="center", width=8)
    table.add_column("Subject", style="green", width=20)
    table.add_column("Book Title", style="white")

    for r in results:
        table.add_row(f"Class {r['class']}", r["subject"], r["title"])

    console.print()
    console.print(table)
    console.print()


def handle_direct_command(data, cmd, args):
    cls, subj_name, book_num, chapter = args
    cls = str(cls)

    if cls not in data:
        console.print(f"[red]Invalid class: {cls}[/red]")
        return

    # Find subject
    subjects = sorted(data[cls].keys())
    subj = None
    for s in subjects:
        if subj_name.lower() in s.lower():
            subj = s
            break

    if not subj:
        console.print(f"[red]Subject not found: {subj_name}[/red]")
        return

    # Find book
    books = [b for b in data[cls][subj] if b.get("code")]
    try:
        book_idx = int(book_num) - 1
        if 0 <= book_idx < len(books):
            book = books[book_idx]
        else:
            console.print(f"[red]Invalid book number[/red]")
            return
    except ValueError:
        console.print(f"[red]Invalid book number[/red]")
        return

    # Get chapter URL
    chap_num = int(chapter)
    url = f"{BASE_URL}{book['code']}{chap_num:02d}.pdf"

    if cmd == "view" or cmd == "open":
        console.print(f"\n[bold]{book['text']} - Chapter {chap_num}[/bold]")
        console.print(f"[cyan]URL:[/cyan] {url}")
        if Confirm.ask("[cyan]Open in browser?[/cyan]", default=True):
            open_in_browser(url)
    elif cmd == "get":
        console.print(url)
    elif cmd == "dl":
        filename = f"{book['text']}_Chapter_{chap_num:02d}.pdf"
        download_chapter(url, filename)


if __name__ == "__main__":
    main()
