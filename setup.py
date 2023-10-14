from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name='fastapi-extras',
    version='2.0.0',
    license='MIT',
    author='Andrew Scott',
    author_email='imgurbot12@gmail.com',
    url='https://github.com/imgurbot12/fastapi-extras',
    description="Utilities to make using fastapi a little easier.",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires='>=3.7',
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'pydantic',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
