from setuptools import setup, find_packages

setup(
    name="agente-suporte-whatsapp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "firebase-admin",
        "requests",
        "python-dotenv",
        "pytest",
        "pytest-cov",
        "pytest-asyncio",
    ],
) 