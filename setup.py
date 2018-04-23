import os
import re
from setuptools import setup, find_packages


def readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
        return readme.read()


def version():
    pattern = re.compile(r'__version__ = \'([\d\.]+)\'')
    with open(os.path.join('sand-python', '__init__.py')) as f:
        data = f.read()
        return re.search(pattern, data).group(1)


setup(
    name='sand-python',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    license='BSD',
    description='A simple Django SAND middleware.',
    long_description='A simple Django SAND middleware.',
    url='https://github.com/coupa/sand-python',
    author='Raghunandan Somaraju',
    author_email='raghunandan.somaraju@coupa.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "Framework :: Django",
    ],
    keywords='django sand',
    install_requires=[
        'django>=1.4',
        'pytest',
    ]
)
