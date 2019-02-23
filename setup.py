import os

from setuptools import find_packages, setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='aplazame',
    author="Jose Gabriel Rivera Rodriguez",
    author_email="jrivera294@gmail.com",
    long_description=read('README.md'),
    packages=find_packages(),
    include_package_data=True,
    cmdclass={},
    install_requires=read('aplazame/requirements/common.txt'),
)
