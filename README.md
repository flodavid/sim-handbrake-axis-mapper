# Map devices reported as "LeafLabs Maple" handbrakes to Linux axis

Sim racing handbrakes sold on websites like AliExpress may not be fully
Linux-compatible, losing the analogue capability. But, since they tend to keep
the generic device name of the board they use, we can read and remap it.  
This script maps the handbrake position to a valid Linux axis for the devices
using "LeafLabs Maple" device name with ID "1EAF:0024".

## Requirements

- python3

## Run

```
python3 -m pip install --upgrade pip
pip install -r requirements.txt
sudo python3 main.py
```

In case of error, see other methods below.

### For debian

As on debian, Python packages are "externally managed" (by apt), the previous 
commands will fail.

Use one of the following options instead.

#### Installing python3 apt package

```shell
sudo apt install python3-evdev
sudo python3 main.py
```

#### With no apt package install, from a bash shell

```bash
python3 -m venv .venv
source .venv/bin/activate # or source .venv/bin/activate.fish for fish

python -m pip install --upgrade pip
pip install -r requirements.txt

sudo python main.py
```
