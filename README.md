# BBHbot

A script to find and react to !BBH commands in comments on the Hive blockchain.

*Please note that this software is in early Beta stage, and that you need to know what you are doing to use it.*

## Installation 

For Ubuntu and Debian install these packages:
```
sudo apt-get install python3-pip build-essential libssl-dev python3-dev python3-setuptools python3-gmpy2
```

### Install Python Packages

Install bbhbot by (you may need to replace pip3 by pip):
```
sudo pip3 install -U bbhbot beem hiveengine
```

## Configure And Run BBHbot

First clone the Github repository to your home directory:
```
cd ~
git clone https://github.com/flaxz/bbhbot
```

After that edit your comment templates using Nano, if you want to change anything, there are 4 comment templates.
```
sudo apt install nano 
cd ~/bbhbot/templates
ls
nano COMMENT-TEMPLATE-1-2-3-4
```

Then edit your configuration file.
```
cd ~/bbhbot
nano bbhbot.config
```

Copy your configuration and comment templates to your working directory.
```
cd ~/bbhbot
sudo cp -R templates /usr/local/bin
sudo cp bbhbot /usr/local/bin
sudo cp bbhbot.config /usr/local/bin
sudo cp run-bbhbot.sh /usr/local/bin
```

Make the startup scripts executable.
```
cd /usr/local/bin
sudo chmod u+x bbhbot
sudo chmod u+x run-bbhbot.sh
```

Copy the Systemd config to it's directory.
```
cd ~/bbhbot
sudo cp bbhbot.service /etc/systemd/system
```

Reload Systemd and start the bot.
```
sudo systemctl daemon-reload
sudo systemctl start bbhbot.service
```

Get status and error messages.
```
sudo systemctl status bbhbot.service
```

Stop the bot.
```
sudo systemctl stop bbhbot.service
```

As has been stated above this bot is in early Beta and bugs and issues are likely to occur.

