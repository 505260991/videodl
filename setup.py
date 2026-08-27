from setuptools import setup, find_packages

setup(
    name='videodl-youku',
    version='0.9.1-youku',
    description='Youku-only downloader optimized for Android Termux',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=['requests>=2.32.5,<3'],
    entry_points={'console_scripts':['videodl=videodl.videodl:main']},
)
