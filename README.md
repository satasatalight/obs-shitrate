## Shitrate!! - Decreases the bitrate of an OBS recording / stream as audio increases.

[**Releases**](https://github.com/satasatalight/obs-shitrate/releases "Releases")

### Requirements:

- [OBS Studio](https://obsproject.com/ "OBS Studio")
- [Python 3.6](https://www.python.org/downloads/release/python-368/ "Python 3.6")
- [The script!!](https://github.com/satasatalight/obs-shitrate/releases "The script!!")

###About

There are two scripts included in this repo, `shitrate.py` and `shitrate-peaks.py`.
- **shitrate.py** will decrease the bitrate directly according to volume levels.
- **shitrate-peaks.py** will decrease the bitrate according to jumps in average volume.

Whichever one you choose is based on personal preference and the effect you are going for. Peaks allows for a more watchable experience while decreasing the bitrate during loud moments for comedic effect while shitrate tends to be more purely chaotic but more accurate to what this project is intended to be.

###Setup

1. Open OBS, go to Tools > Scripting
2. Make sure you have the install path to Python 3.6 correctly listed under *Python Settings*
3. Add the script using the "+" icon.
4. Add all audio sources you want the script to pull volume levels from.
5. Begin recording / streaming! The script automatically enables.

###Tips

- Make sure all sources added are **audio** sources. The script lists all sources at a time, however only audio sources (the ones listed under the *Audio Mixer* tab in OBS) will correctly give volume data.
- Set the maximum bitrate higher than you normally would (~1000+ kbps).
- To minimize how much background noise or generally low noises effect the output bitrate, try increasing the dampening. The minimum dampening value gives a straight linear relationship between volume levels and the bitrate while higher dampening causes volume to follow a concave down quadratic relationship to the bitrate. 
- The default dampening and bitrate values are what I personally found working following [OBS's audio mixer guide](https://obsproject.com/kb/audio-mixer-guide "OBS' audio mixer guide"). 

[![OBS' general guide for where sound levels should be placed in the audio mixer.](https://obsproject.com/media/pages/kb/audio-mixer-guide/635d30015f-1644751140/ecyfthu-1.png "OBS' general guide for where sound levels should be placed in the audio mixer.")](https://obsproject.com/kb/audio-mixer-guide "OBS' general guide for where sound levels should be placed in the audio mixer.")

- Have fun 🙂