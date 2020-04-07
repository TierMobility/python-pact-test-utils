from os.path import join
from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

def get_version():
    with open(join('pact_test_utils', '__init__.py')) as f:
        for line in f:
            if line.startswith('__version__ ='):
                return line.split('=')[1].strip().strip('"\'')

setup(
    name='pact_test_utils',
    version=get_version(),
    description='A wrapper for pactman tests to make them more pythonic',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Tom Wallroth',
    author_email='tom@tier.app',
    url='https://github.com/TierMobility/python-pact-test-utils/',
    license='MIT',
    packages=find_packages(),
    install_requires=['pactman==2.25.0'],
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: MIT License',
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    zip_safe=False,
)