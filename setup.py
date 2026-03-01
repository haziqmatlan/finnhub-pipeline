import os, pathlib, subprocess, sys, setuptools

def package_install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

GIT_TOKEN = os.getenv("GIT_TOKEN")

PACKAGES_REQUIREMENT = [
    "nameparser==1.1.2",
    "PyYAML>=6.0.1",
    "python-dotenv==1.0.0"
    ]

DEV_PACKAGE_REQUIREMENT = [
    "pyspark==3.3.0",
    "dbx>=0.8.19",
    "wheel",
    # "pyyaml==6.0",
    "mlflow",
    "delta-spark==2.1.0",
    "black==22.8.0",
    "numpy==1.23.1",
    "urllib3<2",
    "typing_extensions==4.5.0",
    "psycopg2-binary==2.9.9"
]

current_dir = pathlib.Path(__file__).parent.resolve()
long_description = (current_dir / 'README.md').read_text(encoding='utf-8')

setuptools.setup(
    name="finnhub_data_pipeline",
    version="1.0.1",
    author="Haziq Matlan",
    author_email="haziq.matlan@gmail.com",
    description="This package contains all the necessary classes and functions for data engineering framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(exclude=["**/test/**", "test_*"]),
    entry_points={
        'console_scripts': [
            'finnhub-etl-pipeline = pipelines.entry_point:main' # Set as entry point for ETL - need to be inside `pipelines` package
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    setup_requires=['setuptools', 'wheel'],
    install_requires=PACKAGES_REQUIREMENT,
    extras_require={'dev': DEV_PACKAGE_REQUIREMENT},
    include_package_data=True,
    package_data={
        'data_pipeline.core.validation.config': ['*.csv', '*.json'],
        'data_pipeline.core.validation.yml_query': ["**/*.yml", "**/*.yaml"]
    }
)