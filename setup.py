from setuptools import setup

setup(
        name='ipgw',
        version='0.3.3',
        packages=['ipgw'],
        install_requires=['requests'],
        author='John Jiang',
        author_email='nigelchiang@outlook.com',
        description='NEU IPGW cli tool',
        keywords=['internet', 'cli'],
        license='MIT',
        url='https://github.com/j178/ipgw',
        entry_points={
            'console_scripts': ['ipgw = ipgw.ipgw:main']
        },
        classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',
            'Environment :: Console',
            'Environment :: MacOS X',

            # Indicate who your project is intended for
            'Intended Audience :: End Users/Desktop',
            'Intended Audience :: System Administrators',

            'Topic :: Internet :: WWW/HTTP',

            'Natural Language :: Chinese (Simplified)',
            'Natural Language :: English',

            # Pick your license as you wish (should match "license" above)
            'License :: OSI Approved :: MIT License',

            # Specify the Python versions you support here. In particular, ensure
            # that you indicate whether you support Python 2, Python 3 or both.
            'Programming Language :: Python :: 3.5',
        ],

)
