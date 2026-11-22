"""Optional downloader for the official Boston 311 2024 public CSV.

If Boston changes its export URL, download the 2024 CSV manually from
https://data.boston.gov/dataset/311-service-requests and save it as
`data/raw/boston_311_2024.csv`.
"""
from pathlib import Path
from urllib.request import Request, urlopen

DATA_URL = ("https://data.boston.gov/dataset/8048697b-ad64-4bfc-b090-ee00169f2323/"
            "resource/dff4d804-5031-443a-8409-8344efd0e5c8/download/"
            "lagan_311_open_data_2024_rvsd3.csv")
DEST = Path("data/raw/boston_311_2024.csv")


def main() -> None:
    if DEST.exists():
        print(f"Already present: {DEST}. Delete it first to download again.")
        return
    DEST.parent.mkdir(parents=True, exist_ok=True)
    temporary = DEST.with_suffix(".partial")
    print(f"Downloading official 2024 CSV to {DEST} ...")
    try:
        request = Request(DATA_URL, headers={"User-Agent": "ServicePulse-Portfolio/0.1"})
        with urlopen(request, timeout=90) as source, temporary.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        temporary.replace(DEST)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Saved {DEST} ({DEST.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
