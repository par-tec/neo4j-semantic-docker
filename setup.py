import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="design_d3fend",
    version="0.0.1",
    author="Roberto Polli",
    author_email="robipolli@gmail.com",
    description="A toolkit to support secure architecture design.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/par-tec/github.io/neo4j-semantic-docker",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    keywords=["design", "security", "kubernetes"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={
        "": [
            "mermaidrdf/*.yaml",
            "oasrdf/*.yaml",
            "kuberdf/*.yaml",
            "kuberdf/*.ttl",
        ]
    },
)
