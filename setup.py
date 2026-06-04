from pathlib import Path

from setuptools import find_namespace_packages, setup


ROOT = Path(__file__).parent
README = ROOT.joinpath('README.md').read_text(encoding='utf-8')


setup(
    name='cli-anything-openwebui',
    version='1.0.0',
    description='CLI-Anything harness for operating a running OpenWebUI backend',
    long_description=README,
    long_description_content_type='text/markdown',
    author='ashaiful',
    url='https://github.com/ashaiful/cli-anything-openwebui',
    project_urls={
        'Source': 'https://github.com/ashaiful/cli-anything-openwebui',
        'CLI-Anything': 'https://github.com/HKUDS/CLI-Anything',
        'OpenWebUI': 'https://openwebui.com',
    },
    license='Apache-2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Utilities',
    ],
    packages=find_namespace_packages(include=['cli_anything.*']),
    install_requires=[
        'click>=8.0.0',
        'prompt-toolkit>=3.0.0',
        'requests>=2.28.0',
        'PyYAML>=6.0',
        'keyring>=24.0.0',
    ],
    extras_require={
        'test': ['pytest>=7.0.0'],
    },
    entry_points={
        'console_scripts': [
            'cli-anything-openwebui=cli_anything.openwebui.openwebui_cli:main',
        ],
    },
    package_data={
        'cli_anything.openwebui': ['skills/*.md'],
    },
    include_package_data=True,
    python_requires='>=3.10',
)
