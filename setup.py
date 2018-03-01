"""Setup file."""

from setuptools import find_packages, setup

setup(
    name="Gisi",
    version="2018.03.01",
    description="",
    url="https://github.com/GieselaDev/Gisi",
    author="siku2",
    author_email="siku2@outlook.com",
    license="MIT",
    packages=find_packages(exclude=["docs", "tests"]),
    install_requires=[
        "aiodns",
        "aiohttp",
        "beautifulsoup4",
        "cchardet",
        "colorlog",
        "matplotlib",
        "motor",
        "Pillow",
        "selenium",
        "validators",
        "wordcloud",
        "https://github.com/Rapptz/discord.py/archive/rewrite.zip"
    ]
)
