# Aim High - Tech Tracking System

## First-time git users
Atlassian has a [great tutorial](https://www.atlassian.com/git/tutorials/learn-git-with-bitbucket-cloud) on basic Git commands.

## First time setup (for Macs)

### Homebrew and Git
* Open a terminal (Terminal.app, if you don't have another one you prefer)
* Check if you have homebrew installed
```commandline
    brew -v
```
* If you do not see a version number, install Homebrew: [link](https://brew.sh/)
* Check if you have git installed
```commandline
    git --version
```
* If it is unavailable, install it
```commandline
    brew install git
```

### Python 3.6 and virtualenv
* Check what version of Python you have installed
```commandline
    python --version
```
* If the version is newer than 3.6, great! Skip to the next section. If the version is 2.x, you should try
```commandline
    python3 --version
```
* If `python3` was not found, run:
```commandline
    brew install python3
```
* If `python3` was found, but the version was older than 3.6:
```commandline
    brew upgrade python3
```
* Check what version of `pip` you have:
```commandline
    pip --version
```
* If the command prints out a line that ends in `(python 2.7)`, run
```commandline
    pip3 install virtualenv
```
* If, instead, the command had printed out a line that ended in `(python 3.)`, run
```commandline
    pip install virtualenv
```

### Clone the repository

* [Fork this repository](https://bitbucket.org/ycoreaimhigh/techtracking/fork). This will create a copy of the source
  code on BitBucket.
* Clone your copy of the repository into a folder of your choice (replace <username> with your username)
```commandline
    git clone https://<username>@bitbucket.org/<username>/techtracking.git
```
* Create a remote pointing to the upstream copy of the repository
```commandline
    git remote add upstream git@bitbucket.org:ycoreaimhigh/techtracking.git
```
* Change into this directory
```commandline
    cd techtracking
```
* Set up a virtualenv
```commandline
    virtualenv venv
```

### Install libraries, Postgres, set up database
* [Install Postgres](http://postgresapp.com/)
* Run the newly installed Postgres.app, and click the initialize button
* Activate the virtualenv
```commandline
    source venv/bin/activate
```
* Export secret key
```commandline
    export SECRET_KEY=foo
```
* Install the required libraries
```commandline
    pip install -r requirements.txt
```
* Set up the local database
```commandline
    python manage.py makemigrations
    python manage.py migrate
```
* Create a superuser
```commandline
    python manage.py createsuperuser
```
* Run the setup script
```commandline
    python manage.py setup
```
* Run the local server
```commandline
    python manage.py runserver
```
* Open up the admin interface `http://localhost:8000/admin`
* Create the minimum required entries in the database (weeks, SKUs etc.)
* Exit the virtualenv (when you're done)
```commandline
    deactivate
```

## Running the server or making changes
* Activate the virtualenv
```commandline
    source venv/bin/activate
```
* Export secret key (for email delivery, you'll need to set up `SENDGRID_API_KEY` also)
```commandline
    export SECRET_KEY=foo
```
* Run the local server
```commandline
    python manage.py runserver
```
* Open up `http://localhost:8000` in your favorite browser
* Play around with the app and make changes
* Any changes you save to your working directory will automatically be reflected
  in the web browser. Just hit reload.
* When you're done:
```commandline
    deactivate
```

## Updating your repository to match latest upstream
```commandline
    git pull --rebase upstream master
```
If you see this message:
```commandline
    error: cannot pull with rebase: You have unstaged changes.
    error: please commit or stash them.
```
This means you have made changes to the code. If you want to save your changes:
```commandline
    git add --all .
    git commit -am "<description of changes>"
```
If you do not want to save your changes:
```commandline
    git reset --hard HEAD
```
Now you can try rebasing again
