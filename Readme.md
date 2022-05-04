

## Setting Virtualenv and Dev environment on localhost

```
pip3 install virtualenv

mkdir creditrisk
cd creditrisk
virtualenv venv -p python3
source venv/bin/activate
git clone <repo_url>
cd creditrisk
pip install -r requirements.txt

python run.py
```

## Deployment / update procedure

```

sudo su
cd creditrisk/creditrisk
git pull
ps -ef (and kill the tmux tasks if present)
tmux
source ../venv/bin/activate
python3 run.py
exit terminal!

```