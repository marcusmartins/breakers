import re
import ast
from setuptools import setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')


with open('breakers/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


tests_require = ['pytest', ]


setup(
    name='breakers',
    author='Marcus Martins',
    author_email='',
    version=version,
    url='http://github.com/marcusmartins/breakers',
    packages=['breakers'],
    description='Breakers is a simple python package that'
                'implements the circuit breaker pattern.',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
    ],
    install_requires=[
        'sortedcontainers>=0.9.6',
    ],
    tests_require=tests_require,
    extras_require={'test': tests_require},
)
