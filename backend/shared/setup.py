from setuptools import setup, find_packages

setup(
    name="shared",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115.0",
        "sqlalchemy>=2.0.0",
        "asyncpg>=0.30.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "PyJWT>=2.8.0",
        "httpx>=0.27.0",
    ],
)
