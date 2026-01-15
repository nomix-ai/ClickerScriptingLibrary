## NomixClicker Scripting Library

This is a library of ready-made scripts written in Python and using the free [Clicker API](https://panel.nomixclicker.com/docs).

### What Is Clicker?

NomixClicker is a controlling dongle for iOS. It allows manual control, automatic control via API, and fully autonomous AI mode.

Part of the features are work-in-progress, see the [Roadmap](https://nomixclicker.com/).

<p align="center">
  <img src="res/reddit-script-example.gif" width="480" height="360">
  <br>
  <em style="font-size: 0.85em; opacity: 0.7;">Example: quick script for Reddit warmup.</em>
</p>

### How To Use This Library?

Setup is easy. Just make sure you have Python, and then:

```commandline
pip install -r requirements.txt
```

Buy a Clicker device if you don't have it (delivery takes ~2 weeks to any place in the world), then open the [Panel](https://panel.nomixclicker.com/choose_device) and get your API token.

[Purchase on the official site only.](https://panel.nomixclicker.com/payment)

Make a copy of `config.example.json` and name it `config.json`. Enter your API token and device id in appropriate fields.

Now you can launch any script from the `scripts` folder, for example:

```commandline
python3 -m scripts.airplane-mode-iphone-12
```

Manual control of iPhones will work out-of-the-box, no setup needed.

### Scripts

The Library is designed to be easily extendable. Here are the scripts provided as examples (more will be added):

- [**restart_all_devices.py**](scripts/restart_all_devices.py) - Restarts all devices associated with your account.
- [**airplane-mode-iphone-12.py**](scripts/airplane-mode-iphone-12.py) - Toggles airplane mode on and off on iPhone 12.

