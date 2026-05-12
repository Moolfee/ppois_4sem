from __future__ import annotations


def main() -> int:
    try:
        from moorhuhn.main import main as run_app
    except ModuleNotFoundError as exc:
        if exc.name == "pygame":
            print("pygame is not installed. Run: python3 -m pip install -e .")
            return 1
        raise

    return run_app()


if __name__ == "__main__":
    main()
