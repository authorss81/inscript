from setuptools import setup, find_packages

setup(
    name="inscript-lang",
    version="0.6.0",
    description="InScript — A game-focused programming language",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="InScript Team",
    license="MIT",
    url="https://github.com/inscript-lang/inscript",
    packages=find_packages(include=[
        "inscript", "inscript.*",
        "ai", "ai.*",
        "compiler", "compiler.*",
        "engine", "engine.*",
        "network", "network.*",
        "ui", "ui.*",
        "targets", "targets.*",
    ]),
    py_modules=["inscript", "lexer", "parser", "analyzer", "interpreter",
                "ast_nodes", "environment", "errors", "stdlib", "stdlib_values"],
    entry_points={"console_scripts": ["inscript=inscript:main"]},
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    include_package_data=True,
)
