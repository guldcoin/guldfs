from guldfs import __version__
from setuptools import setup, find_packages

REQUIREMENTS = [line.strip() for line in open("requirements.txt").readlines()]

setup(name='guldfs',
      version=__version__,
      platforms='linux',
      description='Signed, distributed, (optionally) encrypted file system.',
      author='isysd',
      author_email='public@iramiller.com',
      license='MIT',
      url='https://fs.guld.io/',
      packages=find_packages(exclude=['tests', 'tests.*']),
      entry_points={'console_scripts': ['guldfs = guldfs:cli']},
      zip_safe=False,
      include_package_data=True,
      install_requires=REQUIREMENTS,
      classifiers=[
          'Topic :: System :: Filesystems',
          'Development Status :: 4 - Beta',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Topic :: Internet',
          'Topic :: Utilities'
])
