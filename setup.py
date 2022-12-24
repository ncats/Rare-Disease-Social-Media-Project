import setuptools
import subprocess
import os

rdsmproj_version = (
    subprocess.run(["git", "describe", "--tags"], stdout=subprocess.PIPE)
    .stdout.decode("utf-8")
    .strip()
)

if "-" in rdsmproj_version:
    # when not on tag, git describe outputs: "1.3.3-22-gdf81228"
    # pip has gotten strict with version numbers
    # so change it to: "1.3.3+22.git.gdf81228"
    # See: https://peps.python.org/pep-0440/#local-version-segments
    v,i,s = rdsmproj_version.split("-")
    rdsmproj_version = v + "+" + i + ".git." + s

assert "-" not in rdsmproj_version
assert "." in rdsmproj_version

assert os.path.isfile("cf_remote/version.py")
with open("cf_remote/VERSION", "w", encoding="utf-8") as fh:
    fh.write("%s\n" % rdsmproj_version)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rdsmproj",
    version=rdsmproj_version,
    authors = [
    {name='Bradley Karas', email='bradley.karas@gmail.com'},
    {name='Devon Leadman', email='devon.leadman@axleinfo.com'},
    {name='William Kariampuzha', email='William.Kariampuzha@axleinfo.com'}
]
    author_email="Qian.Zhu@nih.gov",
    description="Set of tools for use in research of rare disease related text.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ncats/Rare-Disease-Social-Media-Project",
    packages=setuptools.find_packages(),
    package_data={"rdsmproj": ["VERSION"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.5",
    entry_points={"console_scripts": ["rdsmproj = rdsmproj.main:main"]},
    install_requires=[
        "pandas >= 1.4.2",
    ],
)
