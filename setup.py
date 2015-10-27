from setuptools import setup

import cw_udp_socket_reporter


setup(
    name='cloudwatch-udp-socket-reporter',
    version=cw_udp_socket_reporter.__version__,
    url='https://github.com/RUNDSP/cloudwatch-udp-socket-reporter',
    license='Apache Software License',
    install_requires=[
        'boto>=2.38',
        'python-dateutil>=2.1',
        'requests>=0.2.0'
    ],
    author='Mike Placentra',
    author_email='someone@michaelplacentra2.net',
    description='Reports UDP socket statistics to CloudWatch',
    long_description='',
    scripts=[
        'cw_udp_socket_reporter.py',
    ],
    platforms='any',
    classifiers = [
        'Programming Language :: Python',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
