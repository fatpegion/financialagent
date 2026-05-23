"""Entry point expected by Alibaba Cloud Bailian high-code runtime."""

from financialagent_cloud.app import app, run_app

__all__ = ["app", "run_app"]


if __name__ == "__main__":
    run_app()
