# $ python xbee_fota.py <com port> <ncd update file> <PAN ID> <MAC Address> <Chunk size multiple of 16> <FLY Wait 1, No FLY Wait 0> <Start from last segment 1, Start from first segment 0>
# Example: 
# $ python xbee_fota.py COM4 ./Upgrade.ncd 7FFF 41 DB 74 F9 128 1 1
# In case of using this file for overriding generic board identification you'll need to remove hash from 2 lines before "send_store_manifest" called. "Lines: 287,288"
