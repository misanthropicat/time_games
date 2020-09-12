from setuptools import setup

setup(
    name='TLGame',
    packages=['lingvo_time'],
    include_package_data=True,
    install_requires=[
        'flask', 'wtforms', 'werkzeug', 'click',
        'requests', 'progressbar', 'python-magic-bin==0.4.14'
    ],
)