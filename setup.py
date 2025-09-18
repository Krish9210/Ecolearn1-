from setuptools import setup, find_packages

setup(
    name="ecolearn",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'firebase-admin>=6.2.0',
        'firebase-functions>=0.1.0',
        'google-cloud-firestore>=2.11.1',
        'google-cloud-storage>=2.10.0',
        'Flask>=2.3.2',
        'Flask-CORS>=4.0.0',
        'python-dateutil>=2.8.2',
        'pytz>=2023.3',
        'requests>=2.31.0',
    ],
)
