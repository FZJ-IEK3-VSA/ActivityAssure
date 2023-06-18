import os, setuptools

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "requirements.txt")) as f:
    required_packages = f.read().splitlines()
with open(os.path.join(dir_path, "README.md"), "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lpgvalidation",
    version="0.1.0",
    author="David Neuroth",
    author_email="d.neuroth@fz-juelich.de",
    description="A validation framework for load profile generators",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://jugit.fz-juelich.de/iek-3/groups/urbanmodels/personal/neuroth/lpg-validation-framework",
    include_package_data=True,
    packages=setuptools.find_packages(),
    install_requires=required_packages,
    setup_requires=["setuptools-git"],
    license="MIT",
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],  # TODO: Enter further classifiers if necessary (Read more: https://pypi.org/classifiers/)
    keywords=["lpgvalidation", "load profile generator", "validation"],
)
