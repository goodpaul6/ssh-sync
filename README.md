# ssh-sync
`ssh-sync` allows you to synchronize a directory over a secure shell connection. It also has functionality to allow you to run commands remotely, all without leaving the comfort of your local machine.

# Installation
You need to have Python 3 and pip installed.
```
git clone https://github.com/goodpaul6/ssh-sync
cd ssh-sync
pip install -r requirements.txt
```
You can then run the program with `python ssh-sync.py`.

# Usage
See `ssh-sync.py --help` for help with parameters.

## Running Commands on Remote Machine
You can run arbitrary commands on the remote machine by populating your local directory (created by `ssh-sync`) with a `.command` file. `ssh-sync` will recognize this file and will `cd` to the equivalent directory on the remote machine and execute the commands in this file line by line, piping their output to your local machine.
