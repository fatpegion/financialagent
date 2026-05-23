from setuptools import find_packages, setup


setup(
    name="financialagent-bailian",
    version="0.1.5",
    description="Lightweight Bailian high-code adapter for FinancialAgent",
    packages=find_packages(include=["financialagent_cloud", "financialagent_cloud.*", "deploy_starter", "deploy_starter.*"]),
    py_modules=["main"],
    python_requires=">=3.9",
    install_requires=[
        "fastapi==0.116.1",
        "uvicorn==0.35.0",
        "openai==1.99.9",
    ],
)
