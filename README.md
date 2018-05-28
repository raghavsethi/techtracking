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
* If you do not see a version number, [install Homebrew](https://brew.sh/).
* Check if you have git installed
```commandline
    git --version
```
* If it is unavailable, install it
```commandline
    brew install git
```

### Python 3 and virtualenv
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
* If the command was not found or prints out a line that ends in `(python 2.7)`, run
```commandline
    pip3 install virtualenv
```
* If, instead, the command had printed out a line that ended in `(python 3.)`, run
```commandline
    pip install virtualenv
```

### Clone the repository

* Fork this repository (on GitHub this button is on the top right). This will create a copy of the source
  code in your GitHub account.
* Change to the directory you want to download the code into
```commandline
    cd <directory>
```
* Clone your copy of the repository into a folder of your choice (replace <username> with your username)
```commandline
    git clone https://github.com/<your-github-username>/techtracking.git
```
* Create a remote pointing to the upstream copy of the repository
```commandline
    git remote add upstream https://github.com/raghavsethi/techtracking.git
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
* Install Postgres ([Postgres.app](http://postgresapp.com/) is recommended)
* Configure Postgres (or if you're using Postgres.app, run it and click the initialize button)
* Add Postgres to PATH
```commandline
    export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/latest/bin
```
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
* Set up static files
```commandline
    python manage.py collectstatic
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

## Making changes

### Using PyCharm
* PyCharm is a great IDE for Python and is highly recommended. Download
  the community edition from [JetBrains](https://www.jetbrains.com/pycharm/)
* Install it, and run it to begin setup. Choose settings as appropriate
* When you are at the welcome screen, select 'Open', find the 'techtracking' folder and select it
* Click 'Open'
* On the top bar, next to the green triangular run button, make sure the `runserver` configuration is selected
* Click the run button
* Open up `http://localhost:8000` in your favorite browser
* You can now play around with the app
* Make changes by editing files in the 'checkout' directory
* Any changes you save will trigger a re-run. Just hit reload in your web browser.

### Using the Terminal
* Activate the virtualenv
```commandline
    source venv/bin/activate
```
* Export secret key (for email delivery, you'll need to put in the correct `SENDGRID_API_KEY`)
```commandline
    export SECRET_KEY=foo
    export SENDGRID_API_KEY=foo
```
* Run the local server
```commandline
    python manage.py runserver
```
* Open up `http://localhost:8000` in your favorite browser
* You can now play around with the app
* Make changes by editing files using your favorite text editor
* Any changes you save to your working directory will automatically be reflected
  in the web browser. Just hit reload.
* When you're done:
```commandline
    deactivate
```

## Updating your repository

If there are changes in the master (upstream) version that you want to integrate
into your code, you can rebase your code onto the latest version
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
If you do *not* want to save your changes:
```commandline
    git reset --hard HEAD
```
Now you can try rebasing again
