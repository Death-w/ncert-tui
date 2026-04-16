#!/usr/bin/env python3
"""
NCERT Book Fetcher - Terminal-based utility to search and download NCERT textbooks
"""

import argparse
import json
import shutil
import zipfile
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from pypdf import PdfWriter
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    MofNCompleteColumn,
    TextColumn,
    TaskProgressColumn,
)
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

BASE_URL = "https://ncert.nic.in/textbook/pdf/"
DATA_URL = "https://raw.githubusercontent.com/aayushdutt/ncert-downloader/main/data.json"

try:
    from questionary import Style, prompt, confirm, checkbox, select, autocomplete

    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False

CUSTOM_STYLE = Style(
    [
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green bold"),
        ("pointer", "fg:cyan bold"),
        ("answer", "fg:cyan bold"),
        ("instruction", "fg:#888888"),
        ("separator", "fg:#666666"),
        ("question", "fg:#ffffff bold"),
        ("disabled", "fg:#666666 italic"),
    ]
)


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


def search_books(data, query):
    results = []
    query_lower = query.lower()

    for cls, subjects in data.items():
        for subject, books in subjects.items():
            for book in books:
                if book.get("code"):
                    if (
                        query_lower in subject.lower()
                        or query_lower in book["text"].lower()
                        or query_lower in cls
                    ):
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
[bold cyan]╔══════════════════════════════════════════════════════╗
║                                                              ║
║   [bold white]NCERT Book Fetcher[/bold white] - Official Textbook Downloader    ║
║                                                              ║
║   [dim]Search and download NCERT textbooks (Class 1-12)[/dim]  ║
║                                                              ║
╚══════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner)


def display_search_results(results, query):
    if not results:
        console.print(f"\n[yellow]No results found for '{query}'[/yellow]")
        return

    table = Table(
        title=f"[bold]Search Results for '{query}'[/bold] ({len(results)} books)",
        show_lines=True,
        box=box.ROUNDED,
        expand=True,
    )
    table.add_column("Class", style="cyan", justify="center", width=8)
    table.add_column("Subject", style="green", width=20)
    table.add_column("Book Title", style="white", width=50)

    for r in results:
        table.add_row(f"Class {r['class']}", r["subject"], r["title"])

    console.print()
    console.print(table)
    console.print()


def display_catalog(data, class_filter=None, subject_filter=None):
    classes = sorted(data.keys(), key=int)

    if class_filter:
        classes = [c for c in classes if c == str(class_filter)]

    table = Table(
        title="[bold]NCERT Books Catalog[/bold]",
        show_lines=True,
        box=box.ROUNDED,
        expand=True,
    )
    table.add_column("Class", style="cyan", justify="center", width=8)
    table.add_column("Subject", style="green", width=20)
    table.add_column("Available Books", style="white")

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
    console.print(f"[dim]Total: {len(seen)} subject(s) across {len(classes)} class(es)[/dim]\n")


def interactive_menu(data):
    while True:
        show_banner()
        console.print("[bold]What would you like to do?[/bold]\n")
        console.print("  [cyan]1.[/cyan]  Browse by Class")
        console.print("  [cyan]2.[/cyan]  Search for a book")
        console.print("  [cyan]3.[/cyan]  View full catalog")
        console.print("  [cyan]4.[/cyan]  Download books")
        console.print("  [cyan]5.[/cyan]  Update catalog")
        console.print("  [cyan]0.[/cyan]  Exit\n")

        choice = console.input("[bold cyan]Enter your choice:[/bold cyan] ")

        if choice == "1":
            browse_by_class(data)
        elif choice == "2":
            search_interactive(data)
        elif choice == "3":
            display_catalog(data)
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == "4":
            download_books_interactive(data)
        elif choice == "5":
            fetch_catalog(force=True)
            console.print("[green]Catalog updated![/green]")
        elif choice == "0":
            break
        else:
            console.print("[red]Invalid choice[/red]")


def browse_by_class(data):
    classes = sorted(data.keys(), key=int)

    console.print("\n[bold]Select a Class:[/bold]\n")
    for i, cls in enumerate(classes, 1):
        subjects = list(data[cls].keys())
        console.print(f"  [cyan]{cls:>2}.[/cyan]  Class {cls} ({len(subjects)} subjects)")

    console.print()
    choice = console.input("[bold cyan]Enter class number (or 0 to go back):[/bold cyan] ")

    if choice == "0" or choice not in classes:
        return

    cls = choice
    subjects = sorted(data[cls].keys())

    console.print(f"\n[bold]Class {cls} - Subjects:[/bold]\n")
    for i, subj in enumerate(subjects, 1):
        book_count = len([b for b in data[cls][subj] if b.get("code")])
        console.print(f"  [cyan]{i:>2}.[/cyan]  {subj} [dim]({book_count} books)[/dim]")

    console.print()
    subj_choice = console.input("[bold cyan]Enter subject number (or 0 to go back):[/bold cyan] ")

    if subj_choice == "0" or int(subj_choice) > len(subjects):
        return

    subj_idx = int(subj_choice) - 1
    subj = subjects[subj_idx]
    books = [b for b in data[cls][subj] if b.get("code")]

    table = Table(title=f"[bold]Class {cls} - {subj}[/bold]", show_lines=True, box=box.ROUNDED)
    table.add_column("Book", style="white")

    for book in books:
        table.add_row(book["text"])

    console.print()
    console.print(table)
    console.print()

    if confirm("Would you like to download all these books?").ask():
        download_specific_books(data, [(cls, subj, books)])


def search_interactive(data):
    console.print()
    query = console.input("[bold cyan]Enter search query:[/bold cyan] ")

    if not query.strip():
        return

    results = search_books(data, query)
    display_search_results(results, query)

    if results and confirm("Download all these books?").ask():
        download_specific_books(
            data,
            [
                (
                    r["class"],
                    r["subject"],
                    [
                        {
                            "text": r["title"],
                            "code": r["code"],
                            "chapters": r["chapters"],
                        }
                    ],
                )
                for r in results
            ],
        )


def download_books_interactive(data):
    console.print("\n[bold]Download Mode[/bold]\n")
    console.print("  [cyan]1.[/cyan]  Download by Class")
    console.print("  [cyan]2.[/cyan]  Search and Download")
    console.print("  [cyan]3.[/cyan]  Download specific Subject")
    console.print("  [cyan]0.[/cyan]  Go Back\n")

    choice = console.input("[bold cyan]Enter choice:[/bold cyan] ")

    if choice == "1":
        download_by_class(data)
    elif choice == "2":
        search_and_download(data)
    elif choice == "3":
        download_subject(data)


def download_by_class(data):
    classes = sorted(data.keys(), key=int)

    console.print("\n[bold]Select Class to Download:[/bold]\n")
    for cls in classes:
        console.print(f"  [cyan]{cls:>2}.[/cyan]  Class {cls}")

    console.print()
    choice = console.input("[bold cyan]Enter class number:[/bold cyan] ")

    if choice not in classes:
        return

    cls = choice
    subjects = sorted(data[cls].keys())

    console.print(f"\n[bold]Class {cls} - Select Subject(s):[/bold]\n")
    for i, subj in enumerate(subjects, 1):
        book_count = len([b for b in data[cls][subj] if b.get("code")])
        console.print(f"  [cyan]{i:>2}.[/cyan]  {subj} [dim]({book_count} books)[/dim]")

    console.print()
    subj_choices = console.input(
        "[bold cyan]Enter subject numbers (comma-separated, or 'all'):[/bold cyan] "
    )

    if subj_choices.lower() == "all":
        selected = [(cls, subj, [b for b in data[cls][subj] if b.get("code")]) for subj in subjects]
    else:
        selected = []
        for idx in subj_choices.split(","):
            idx = idx.strip()
            if idx.isdigit() and 1 <= int(idx) <= len(subjects):
                subj = subjects[int(idx) - 1]
                selected.append((cls, subj, [b for b in data[cls][subj] if b.get("code")]))

    if selected:
        download_specific_books(data, selected)


def search_and_download(data):
    console.print()
    query = console.input("[bold cyan]Search books:[/bold cyan] ")

    if not query.strip():
        return

    results = search_books(data, query)

    if not results:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return

    display_search_results(results, query)

    console.print("  [cyan]all[/cyan]  Download all results")
    choice = console.input(
        "\n[bold cyan]Enter book numbers to download (comma-separated):[/bold cyan] "
    )

    if choice.lower() == "all":
        selected_codes = [r["code"] for r in results]
    else:
        selected_codes = []
        for idx in choice.split(","):
            idx = idx.strip()
            if idx.isdigit() and 1 <= int(idx) <= len(results):
                selected_codes.append(results[int(idx) - 1]["code"])

    if selected_codes:
        books_to_download = []
        for r in results:
            if r["code"] in selected_codes:
                books_to_download.append(
                    (
                        r["class"],
                        r["subject"],
                        [
                            {
                                "text": r["title"],
                                "code": r["code"],
                                "chapters": r["chapters"],
                            }
                        ],
                    )
                )
        download_specific_books(data, books_to_download)


def download_subject(data):
    classes = sorted(data.keys(), key=int)

    console.print("\n[bold]Download Specific Subject[/bold]\n")

    subj_query = console.input("[bold cyan]Enter subject name to search:[/bold cyan] ").strip()

    if not subj_query:
        return

    matching_subjects = []
    for cls in classes:
        for subj in data[cls].keys():
            if subj_query.lower() in subj.lower():
                book_count = len([b for b in data[cls][subj] if b.get("code")])
                matching_subjects.append((cls, subj, book_count))

    if not matching_subjects:
        console.print(f"[yellow]No subjects found matching '{subj_query}'[/yellow]")
        return

    table = Table(title=f"Matching Subjects for '{subj_query}'", box=box.ROUNDED)
    table.add_column("#", style="cyan", justify="center", width=4)
    table.add_column("Class", style="white", width=8)
    table.add_column("Subject", style="green")
    table.add_column("Books", style="dim", width=8)

    for i, (cls, subj, count) in enumerate(matching_subjects, 1):
        table.add_row(str(i), f"Class {cls}", subj, str(count))

    console.print()
    console.print(table)
    console.print()

    choice = console.input("[bold cyan]Enter number to select (or 0 to cancel):[/bold cyan] ")

    if choice.isdigit() and 1 <= int(choice) <= len(matching_subjects):
        cls, subj, _ = matching_subjects[int(choice) - 1]
        books = [b for b in data[cls][subj] if b.get("code")]
        download_specific_books(data, [(cls, subj, books)])


def download_specific_books(data, selections, output_dir=None):
    if not output_dir:
        output_dir = Path.home() / "NCERT_Books"

    output_dir.mkdir(parents=True, exist_ok=True)

    books_to_download = []
    for cls, subject, books in selections:
        for book in books:
            if book.get("code"):
                dest = output_dir / f"Class_{cls}" / subject / f"{book['text']}.zip"
                books_to_download.append(
                    {"class": cls, "subject": subject, "book": book, "dest": dest}
                )

    if not books_to_download:
        console.print("[yellow]No books to download[/yellow]")
        return

    console.print(f"\n[bold]Downloading {len(books_to_download)} book(s) to:[/bold]")
    console.print(f"  [cyan]{output_dir}[/cyan]\n")

    concurrency = 5
    completed = 0
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Downloading...", total=len(books_to_download))

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(download_single_book, item): item for item in books_to_download
            }

            for future in as_completed(futures):
                item = futures[future]
                result = future.result()

                if result["success"]:
                    completed += 1
                    progress.update(
                        task,
                        advance=1,
                        description=f"[green]Downloaded {completed}/{len(books_to_download)}",
                    )
                else:
                    errors.append(f"{item['book']['text']}: {result.get('error', 'Unknown error')}")
                    progress.update(
                        task,
                        advance=1,
                        description=f"[yellow]Progress: {completed}/{len(books_to_download)}",
                    )

    console.print()

    if errors:
        console.print("[bold red]Download Errors:[/bold red]")
        for err in errors:
            console.print(f"  [red]✗[/red]  {err}")
        console.print()

    if sys.stdin.isatty():
        merge_choice = confirm("Merge downloaded files into PDFs?").ask()
    else:
        merge_choice = True
        console.print("[dim]Auto-merging files (non-interactive mode)[/dim]")

    if merge_choice:
        merge_all_books(output_dir)


def download_single_book(item, max_retries=3):
    dest = item["dest"]

    if dest.exists():
        return {"success": True, "skipped": True}

    url = f"{BASE_URL}{item['book']['code']}dd.zip"
    tmp = None

    for attempt in range(max_retries):
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".zip.tmp")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, stream=True, timeout=60, headers=headers)
            response.raise_for_status()

            with open(tmp, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            tmp.rename(dest)
            return {"success": True}

        except Exception as e:
            if tmp and tmp.exists():
                tmp.unlink()
            if attempt < max_retries - 1:
                import time

                time.sleep(1)
                continue
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Max retries exceeded"}


def merge_all_books(output_dir):
    zip_files = list(output_dir.rglob("*.zip"))

    if not zip_files:
        console.print("[yellow]No zip files found to merge[/yellow]")
        return

    console.print(f"\n[bold]Merging {len(zip_files)} book(s) into PDFs...[/bold]\n")

    completed = 0
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Merging...", total=len(zip_files))

        for zip_file in zip_files:
            result = merge_single_book(zip_file)

            if result["success"]:
                completed += 1
                progress.update(
                    task,
                    advance=1,
                    description=f"[green]Merged {completed}/{len(zip_files)}",
                )
            else:
                errors.append(f"{zip_file.stem}: {result.get('error', 'Unknown error')}")
                progress.update(task, advance=1)

    console.print()

    if errors:
        console.print("[bold red]Merge Errors:[/bold red]")
        for err in errors:
            console.print(f"  [red]✗[/red]  {err}")

    console.print(f"\n[bold green]Done![/bold green]")
    console.print(f"Books saved to: [cyan]{output_dir}[/cyan]\n")


def merge_single_book(zip_path, keep_zip=False):
    out_pdf = zip_path.with_suffix(".pdf")

    if out_pdf.exists():
        return {"success": True, "skipped": True}

    temp_dir = zip_path.parent / f"_tmp_{zip_path.stem}"

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)

        pdf_files = sorted(temp_dir.rglob("*.pdf"))

        if not pdf_files:
            return {"success": False, "error": "No PDFs found in archive"}

        if len(pdf_files) > 1 and "prelim" in str(pdf_files[0]).lower():
            prelim = [f for f in pdf_files if "prelim" in str(f).lower()]
            others = [f for f in pdf_files if "prelim" not in str(f).lower()]
            pdf_files = prelim + others

        writer = PdfWriter()
        for pdf in pdf_files:
            writer.append(str(pdf))

        with open(out_pdf, "wb") as f:
            writer.write(f)

        if not keep_zip:
            zip_path.unlink()

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def open_folder(path):
    path = Path(path).expanduser()
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", str(path)])
    elif sys.platform == "win32":
        subprocess.run(["explorer", str(path)])
    else:
        console.print(f"[cyan]Open folder: {path}[/cyan]")


def main():
    parser = argparse.ArgumentParser(
        description="NCERT Book Fetcher - Download NCERT textbooks from the official website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-s", "--search", metavar="QUERY", help="Search for books")
    parser.add_argument(
        "-c",
        "--class",
        dest="cls",
        metavar="N",
        type=int,
        help="Filter by class (1-12)",
    )
    parser.add_argument("--subject", metavar="NAME", help="Filter by subject")
    parser.add_argument("-l", "--list", action="store_true", help="List available books")
    parser.add_argument("-o", "--output", metavar="DIR", default=None, help="Output directory")
    parser.add_argument("--update-catalog", action="store_true", help="Force update book catalog")
    parser.add_argument("--open", action="store_true", help="Open downloads folder after download")

    args = parser.parse_args()

    data = fetch_catalog(force=args.update_catalog)

    if args.list:
        display_catalog(data, args.cls, args.subject)
        return

    if args.search:
        results = search_books(data, args.search)
        display_search_results(results, args.search)
        return

    if not sys.stdin.isatty():
        console.print(
            "[yellow]Non-interactive mode: Use --search, --list, or --class options[/yellow]"
        )
        return

    interactive_menu(data)


if __name__ == "__main__":
    main()
