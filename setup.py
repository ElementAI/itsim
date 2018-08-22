from setuptools import setup
# from subprocess import check_output

with open("README.md", "r") as file_long_description:
    long_description = file_long_description.read()

setup(
    name='itsim',
    version='0.0.1',
    packages=['itsim'],
    data_files=[('.', ['LICENSE'])],
    install_requires=['greensim'],
    description='IT infrastructure and cyberattack simulation toolkit',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ElementAI/itsim",
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    )
)
