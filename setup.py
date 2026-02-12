"""
Setup configuration for ConComplyAI - Construction Compliance AI System
"""
from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

setup(
    name="concomplai",
    version="2.0.0",
    description="Construction Compliance AI - Multi-agent system for OSHA and NYC Building Code compliance",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="ConComplyAI Team",
    author_email="info@concomplai.ai",
    url="https://github.com/NickAiNYC/ConComplyAi",
    packages=find_packages(include=['core', 'core.*', 'backend', 'backend.*', 'concomplyai', 'concomplyai.*']),
    install_requires=read_requirements(),
    python_requires='>=3.12.0',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    entry_points={
        'console_scripts': [
            'concomplai-api=core.api:main',
            'concomplai-worker=backend.celery_worker:main',
            'concomplai-platform=concomplyai.api.app:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
