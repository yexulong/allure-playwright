import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pytest_playwright_allure",
    version="0.0.2",
    author="yexulong",
    author_email="yexulong@foxmail.com",
    description="A pytest plugin for Playwright to attach allure report",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yexulong/allure-playwright",
    packages=["allure_playwright"],
    include_package_data=True,
    install_requires=[
        "playwright>=1.18",
        "pytest>=6.2.4,<8.0.0",
        "pytest-base-url>=1.0.0,<3.0.0",
        "python-slugify>=6.0.0,<9.0.0",
        "allure-pytest>=2.13.2",
    ],
    entry_points={"pytest11": ["pytest_playwright_allure = allure_playwright.allure_playwright"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Pytest",
    ],
    python_requires=">=3.8",
)
