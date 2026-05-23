"""Local and cloud entry point for FinancialAgent."""

from financialagent_cloud.app import app, run_app

__all__ = ["app", "run_app"]


if __name__ == "__main__":
    run_app()
