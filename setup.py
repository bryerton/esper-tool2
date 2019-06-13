from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
   name="esper-tool2",
   author="Bryerton Shaw",
   author_email="bryerton@gmail.com",
   description="Command line tool for accessing ESPER version 2",
   license='MIT',
   long_description=long_description,
   long_description_content_type="text/markdown",
   url="https://github.com/bryerton/esper-tool2",
   use_scm_version=True,
   setup_requires=['setuptools_scm', 'pytest-runner'],
   classifiers=[
      # How mature is this project? Common values are
      #   3 - Alpha
      #   4 - Beta
      #   5 - Production/Stable
      'Development Status :: 5 - Production/Stable',

      # Indicate who your project is intended for
      'Intended Audience :: Science/Research',
      'Environment :: Console',
      'Topic :: System :: Networking',
      "License :: OSI Approved :: MIT License",
      "Operating System :: OS Independent",
      # Specify the Python versions you support here. In particular, ensure
      # that you indicate whether you support Python 2, Python 3 or both.
      'Programming Language :: Python :: 3',
   ],
   keywords='esper monitoring control experiments',
   tests_require=["pytest"],

   # You can just specify the packages manually here if your project is
   # simple. Or you can use find_packages().
   packages=find_packages('src'),
   package_dir={'': 'src'},

   # Alternatively, if you want to distribute just a my_module.py, uncomment
   # this:
   #   py_modules=["my_module"],

   # List run-time dependencies here.  These will be installed by pip when
   # your project is installed. For an analysis of "install_requires" vs pip's
   # requirements files see:
   # https://packaging.python.org/en/latest/requirements.html
   install_requires=['requests', 'datetime', 'ipaddress', 'futures'],

   # List additional groups of dependencies here (e.g. development
   # dependencies). You can install these using the following syntax,
   # for example:
   # $ pip install -e .[dev,test]
   # extras_require={
   #    'dev': ['check-manifest'],
   #    'test': ['coverage'],
   # },

   # If there are data files included in your packages that need to be
   # installed, specify them here.  If using Python 2.6 or less, then these
   # have to be included in MANIFEST.in as well.
   include_package_data=True,

   # Although 'package_data' is the preferred approach, in some case you may
   # need to place data files outside of your packages. See:
   # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
   # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
   # data_files=[('my_data', ['data/data_file'])],

   # To provide executable scripts, use entry points in preference to the
   # "scripts" keyword. Entry points provide cross-platform support and allow
   # pip to create the appropriate form of executable for the target platform.
   entry_points={
      'console_scripts': [
         'esper-tool2 = espertool.cli:main'
      ]
   }
)
