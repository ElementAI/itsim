# Notes for deploying notebooks on Binder

Binder uses a requirements.txt file to create a docker image containing the proper python packages. 

To generate a new requirements.txt file for binder: 

1- Keep required packages in Pipfile

2- Install packages into environment: 
    $ pipenv install

3- Create new requirements.txt file
    $pipenv run pip freeze > requirements.txt

Setting up Binder: 
https://media.readthedocs.org/pdf/mybinder/latest/mybinder.pdf
https://mybinder.org/
    
    
    
    
