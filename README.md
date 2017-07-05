# Aim High - Tech Tracking System

## First time setup (for Macs)

* Open Terminal.app
* Install [Homebrew](https://brew.sh/) (if you haven't already)
* Install Python 3 (if you haven't already)
```commandline
    brew install python3
```
* Install virtualenv
```commandline
    pip install virtualenv
```
* Install git
```commandline
    brew install git
```
* [Fork this repository](https://bitbucket.org/ycoreaimhigh/techtracking/fork)
* Clone your copy of the repository into a folder of your choice (replace raghavsethi with your username)
```commandline
    git clone git@bitbucket.org:raghavsethi/techtracking.git
```
* Change into this directory
```commandline
    cd techtracking
```
* Set up a virtualenv
```commandline
    virtualenv venv
```
* Activate the virtualenv
```commandline
    source venv/bin/activate
```
* Install libraries
```commandline
    pip install -r requirements.txt
```
* Set up database
```commandline
    python manage.py makemigrations
    python manage.py migrate
```

* To exit the virtualenv (when you're done)
```commandline
    deactivate
```

## Running the server
* Run the local server
```commandline
    python manage.py runserver
```
* Open up `http://localhost:8000` in your favorite browser
* Any changes you save to your working directory will automatically be reflected
  in the web browser. Just hit reload.
