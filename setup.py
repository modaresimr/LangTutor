from setuptools import setup, find_packages

setup(
    name='langtutor',
    version='1.0.0',
    author='Ali Modaresi',
    author_email='modaresimr@gmail.com',
    description='Description of your project',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/modaresimr/LangTutor',
    packages=find_packages(where='langtutor'),
    
    install_requires=open('requirements.txt').readlines(),

    entry_points={
        'console_scripts': [
            'langtutor = langtutor.__main__:main'
        ]
    },
    python_requires='>=3.6',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
