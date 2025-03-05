from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="voice-agent",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A voice agent system that handles inbound and outbound calls using VAPI, N8N, and Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/voice-agent",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/voice-agent/issues",
        "Documentation": "https://github.com/yourusername/voice-agent/blob/main/README.md",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Telephony",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    package_dir={"": "app"},
    packages=find_packages(where="app"),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.110.1",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.6.0",
        "pydantic-settings>=2.1.0",
        "sqlalchemy>=2.0.27",
        "alembic>=1.13.1",
        "httpx>=0.27.0",
        "anthropic>=0.16.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-dotenv>=1.0.1",
        "tenacity>=8.2.3",
        "loguru>=0.7.2",
        "jinja2>=3.1.3",
        "orjson>=3.9.12",
        "asyncpg>=0.28.0",
        "redis>=5.0.1",
        "aiofiles>=23.2.1",
        "python-multipart>=0.0.7",
        "email-validator>=2.1.0",
        "phonenumbers>=8.13.16",
        "celery>=5.3.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.5",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.4.1",
            "flake8>=6.1.0",
            "pre-commit>=3.3.3",
            "faker>=22.2.0",
            "pytest-mock>=3.12.0",
        ],
        "prod": [
            "gunicorn>=21.2.0",
            "sentry-sdk[fastapi]>=1.39.2",
            "prometheus-client>=0.17.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "voice-agent=app.main:start_app",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["templates/*.txt", "static/*"],
    },
)