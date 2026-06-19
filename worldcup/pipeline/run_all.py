"""Run the whole pipeline: fetch, build, model.

    python run_all.py            # fetch live where possible, then build + model
    python run_all.py --offline  # skip network fetches, use the committed snapshots

Each fetch step is best-effort: a network failure leaves the existing snapshot in
place and the pipeline continues, so the model and live tool always produce output.
"""
import sys

import build_expectations
import build_interest
import build_pedigree
import build_workbook
import model


def main():
    offline = "--offline" in sys.argv
    if not offline:
        try:
            import fetch_worldbank
            print("== World Bank =="); fetch_worldbank.main()
        except Exception as exc:  # noqa: BLE001
            print(f"World Bank fetch skipped: {exc}")
        try:
            import fetch_elo
            print("== Elo =="); fetch_elo.main()
        except Exception as exc:  # noqa: BLE001
            print(f"Elo fetch skipped: {exc}")
        try:
            import fetch_trends
            print("== Google Trends =="); fetch_trends.main()
        except Exception as exc:  # noqa: BLE001
            print(f"Trends fetch skipped: {exc}")
        try:
            import fetch_results
            print("== Results =="); fetch_results.main()
        except Exception as exc:  # noqa: BLE001
            print(f"Results fetch skipped: {exc}")

    print("== Interest composite =="); build_interest.main()
    print("== Pedigree =="); build_pedigree.main()
    print("== Workbook =="); build_workbook.main()
    print("== Expectations (Monte Carlo) =="); build_expectations.main()
    print("== Model =="); model.main()


if __name__ == "__main__":
    main()
