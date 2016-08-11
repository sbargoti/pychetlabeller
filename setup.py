#!/usr/bin/env python

from distutils.core import setup

setup(name='Distutils',
	version='1.0',
	description='Python geometry labeller for images',
	author='Suchet Bargoti',
	# author_email='',
	url='https://github.com/sbargoti/pychetlabeller',
	package_dir={'pychetlabeller': 'src/pychetlabeller'},
	packages=['pychetlabeller'],
	# package_data={'pychetlabeller': ['pychetlabeller/*.dat']},
	)

