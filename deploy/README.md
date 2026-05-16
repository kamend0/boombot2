# Deploying boombot to a Vultr VPS

Tested target: Ubuntu 24.04, $5/mo tier. Everything below assumes a fresh box.

## 0. Before creating the VPS

Generate an SSH key on your Mac (skip if you already have `~/.ssh/id_ed25519`):

```bash
ssh-keygen -t ed25519 -C "you@example.com"
pbcopy < ~/.ssh/id_ed25519.pub
```

In the Vultr dashboard, paste the pubkey into **SSH Keys**, then attach it when creating the instance. This pre-installs your key for `root`, so the first login is keys-only.

Optional but nice — add a host alias in `~/.ssh/config` on your Mac:

```
Host boombot
    HostName <vps-ip>
    User boombot
    IdentityFile ~/.ssh/id_ed25519
```

After step 2 below, `ssh boombot` will just work.

## 1. System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ffmpeg libopus0 libsodium23 ca-certificates curl git \
    ufw fail2ban unattended-upgrades
```

`ffmpeg` is required for audio. `libopus`/`libsodium` are needed by discord.py's voice support.

## 2. Create a service user

```bash
sudo useradd -m -s /bin/bash boombot
sudo usermod -aG sudo boombot

# Copy your SSH key from root to boombot so you can log in directly:
sudo mkdir -p /home/boombot/.ssh
sudo cp /root/.ssh/authorized_keys /home/boombot/.ssh/authorized_keys
sudo chown -R boombot:boombot /home/boombot/.ssh
sudo chmod 700 /home/boombot/.ssh
sudo chmod 600 /home/boombot/.ssh/authorized_keys
```

Now `ssh boombot@<vps-ip>` works. Verify in a **new** terminal before continuing. The rest of the steps run as the `boombot` user unless noted.

## 3. Harden the box

These aren't bot-specific, just sane VPS hygiene. Run as a sudoer.

### Firewall (outbound-only bot, so just allow SSH)

```bash
sudo ufw allow OpenSSH
sudo ufw enable
```

### Lock down SSH

Edit `/etc/ssh/sshd_config`:

```
PasswordAuthentication no
PermitRootLogin prohibit-password
```

Then:

```bash
sudo sshd -t                  # validate config — DO NOT skip
sudo systemctl restart ssh
```

Keep your current session open while you confirm a new one still works. If you brick SSH, use Vultr's web console with the emailed root password to recover.

### Unattended security upgrades

```bash
sudo dpkg-reconfigure -plow unattended-upgrades   # answer "Yes"
```

### Persistent system logs

By default Ubuntu's journal is wiped on reboot. Make it persistent so `journalctl -u boombot --since yesterday` survives restarts:

```bash
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
```

### Timezone (optional)

```bash
sudo timedatectl set-timezone America/Los_Angeles
```

### Swap (recommended on the 1GB tier)

Note: vultr or Ubuntu might already have this enabled for you. Check:

```bash
swapon --show
ls -lh /swapfile
free -h
```

`swapon` should list the swapfile. `ls` should confirm it. `free -h` should show free 
memory and swap available. If you don't see anything here, then...

Since ffmpeg + Python + voice can spike RAM, 2GB of swap prevents an OOM kill:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 4. Install uv

As the `boombot` user:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
```

## 5. Clone and install

```bash
cd ~
git clone <your-repo-url> boombot2
cd boombot2
uv sync           # creates .venv and installs deps, fetching Python 3.14 if needed
```

## 6. Configure

```bash
cp .env.example .env
# Edit .env: fill in DISCORD_TOKEN, DISCORD_GUILD_ID, AWS creds, S3_BUCKET, etc.
chmod 600 .env
```

## 7. Push sound files

From your local machine:

```bash
ssh boombot 'mkdir -p ~/boombot2/sounds'
scp ./sounds/*.mp3 boombot:/home/boombot/boombot2/sounds/
```

Only `.mp3` files are recognized.

## 8. Test in the foreground

```bash
uv run python -m boombot.bot
```

Watch for "Logged in as ..." and "Synced N slash commands". Hit Ctrl-C to stop.

## 9. Install systemd unit

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

## 10. Updates later

```bash
ssh boombot
cd ~/boombot2
git pull
uv sync
sudo systemctl restart boombot
```

## AWS / S3 setup

Create an IAM **user** (not role — roles are for AWS-hosted compute) with this inline policy. Replace `<bucket>` and adjust the key if you changed `S3_ALIASES_KEY`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::<bucket>/boombot/aliases.json"
  }]
}
```

Generate an access key for that user and put it in `.env` as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. No `ListBucket` or `DeleteObject` needed — the bot only `GetObject`s and `PutObject`s a single known key.
