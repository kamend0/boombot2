# Deploying boombot to a Vultr VPS

Tested target: Ubuntu 24.04, $5/mo tier. Everything below assumes a fresh box.

## 1. System packages

```bash
sudo apt update
sudo apt install -y ffmpeg libopus0 libsodium23 ca-certificates curl git
```

`ffmpeg` is required for audio. `libopus`/`libsodium` are needed by discord.py's voice support.

## 2. Create a service user

```bash
sudo useradd -m -s /bin/bash boombot
sudo -iu boombot
```

The rest of the steps run as the `boombot` user unless noted.

## 3. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Reload PATH:
source ~/.local/bin/env
```

## 4. Clone and install

```bash
cd ~
git clone <your-repo-url> boombot2
cd boombot2
uv sync           # creates .venv and installs deps, fetching Python 3.14 if needed
```

## 5. Configure

```bash
cp .env.example .env
# Edit .env: fill in DISCORD_TOKEN, DISCORD_GUILD_ID, AWS creds, S3_BUCKET, etc.
chmod 600 .env
```

## 6. Push sound files

From your local machine:

```bash
scp -r ./sounds/* boombot@<vps-ip>:/home/boombot/boombot2/sounds/
```

(Create the dir first on the VPS: `mkdir -p ~/boombot2/sounds`.)

## 7. Test in the foreground

```bash
uv run python -m boombot.bot
```

Watch for "Logged in as ..." and "Synced N slash commands". Hit Ctrl-C to stop.

## 8. Install systemd unit

As root:

```bash
sudo cp /home/boombot/boombot2/deploy/boombot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now boombot
```

Check status / logs:

```bash
sudo systemctl status boombot
sudo journalctl -u boombot -f
# Or the rotating files:
tail -f /home/boombot/boombot2/logs/boombot.log
```

## 9. Updates later

```bash
sudo -iu boombot
cd ~/boombot2
git pull
uv sync
sudo systemctl restart boombot
```

## AWS / S3 setup

Create an IAM user with this policy (replace `<bucket>` and `<key>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::<bucket>/<key>"
  }]
}
```

Generate an access key and put it in `.env`. That's it.
