### payloads: tiny programs launched by spft-replay

The payloads could be either standalone (implementing their own functionality) or *piggyback* on top of existing Download Agent binaries provided by Mediatek.

### Build dependencies (Debian 11)

1. Base building tools (`apt install build-essential`)
2. Some `arm-none-eabi` toolchain (`apt install gcc-arm-none-eabi` **or** provide your own toolchain path prefix using the `CROSS_COMPILE` environment variable)
3. `wget` for downloading SP Flash Tool archives (`apt install wget`)
4. `7z` for extracting archives (`apt install p7zip-full`)
5. Python 3.6+
6. Keystone framework for patching Download Agents (`pip install keystone-engine`)

### License
GPLv3, except the `Makefile` which is Unlicense because I wasn't sure about the included disassembled code.
