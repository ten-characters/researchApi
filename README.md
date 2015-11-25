# api

### Setup Guide:

0. Install monogodb (3.0.x) or newest (make sure compatible)
1. Create database
2. Create mongo user: API with credentials: 
    db.createUser( {
    user:'admin',
    pwd:'password', 
    roles:[ { role: "readWrite", db: "database" } ]
    }
)
3. Install python3.4  
    * Create virtualenv for api  
    * Install from the requirements file: pip install -r requirements.txt  
4. Install jpeg libs with sudo apt-get install libjpeg-dev  
5. Install aws command line interface (using pip)  
6. Setup aws with credentials:  
    * COMMAND: aws configure
    * access_key:'access',
    * secret_key:'secret'
    * region:'us-east-1'
7. Install wkhtmltopdf with sudo apt-get install wkhtmltopdf  
8. https://github.com/JazzCore/python-pdfkit/blob/master/travis/before-script.sh  
8.1. ^ For ubuntu/debian  
    
## Some Explanations

### Updating to V1.1 from V1.0  
Open the python3.4 console and import run_updater from APP.mongoUpdater  
Run it!
