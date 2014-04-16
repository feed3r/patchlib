from distutils.core import setup

setup(name = 'patchlib',
      version = '1.14',
      description = 'Package to process and inspect patches and diffs',
      license = 'MIT',
      author = 'Anatoly Techtonik; Francesco Romani',
      maintainer = 'Francesco Romani',
      maintainer_email = 'fromani@gmail.com',
      url = 'http://github.com/mojaves/patchlib',
      py_modules = [ 'patchlib' ],
      scripts=[ 'scripts/patch' ],
      classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities'
      ])
