from setuptools import setup, find_packages

setup(
    name='scene_graph_sim',
    version='0.1.0',
    packages=find_packages(where='python_package'),
    package_dir={'': 'python_package'},
    install_requires=[
        # Add your package dependencies here
    ],
    
    description='A package for simulating scene graphs',
    python_requires='>=3.8',
)