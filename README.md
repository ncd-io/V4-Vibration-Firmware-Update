# V4-Vibration-Firmware-Update

In order to update the fimrware you will need a

USB to Serial Converter Windows PC Board name PR55-88 Note : if the file name has any special char please remove it

Make sure the PC has usb-serial driver https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads

To update the firmware, you will need a

USB to Serial Converter(PR55-68 or any USB to serial) Windows PC Board name PR55-81 Note: if the file name has any special char, please remove it

How to put in program mode

Press and hold cfg button

Press and release the RST button

Release RST button

Once the firmware update is finished, device will reboot

COmmand to start fimrware update -- python ncd_py_bootloader_v2.py COM4 ./Upgrade.ncd 240
