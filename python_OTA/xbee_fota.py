# Syntax 
# $ python xbee_fota.py <com port> <ncd update file> <PAN ID> <MAC Address> <Chunk size multiple of 16> <FLY Wait 1, No FLY Wait 0> <Start from last segment 1, Start from first segment 0>
# Example: 
# $ python xbee_fota.py COM4 ./Upgrade.ncd 7FFF 41 DB 74 F9 128 1 1
# In case of using this file for overriding generic board identification you'll need to remove hash from 2 lines before "send_store_manifest" called. "Lines: 287,288"
from pyxbee_lib import xbee 
import sys 
import time

FOTA_CMD_HDR=0xF5
COMM_CMD_HDR=0xF7
START_FOTA_MODE_CMD_ID=0x38
END_FOTA_MODE_CMD_ID=0x39
READ_CURRENT_MANIFEST_CMD_ID=0x3C
PGM_FOTA_MANIFEST_CMD_ID=0x3A
PGM_FOTA_MEMORY_CMD_ID=0x3B
READ_FOTA_MANIFEST_CMD_ID=0x3C
GET_LAST_FOTA_PGM_SEGMENT=0x3D
MIN_FLY_PACKET_LEN=12
RUN_MODE_MSG_HDR=0x7F
CMD_RSP_HDR=0x7C
FOTA_MODE_PAN_ID=0x7AAA
REBOOT_CMD=0x40
RETRIALS = 3

def resp_packet_decoder(address, source_addr, payload):
    ack = False
    status = 0x00
    param = []
    if (source_addr == address):
        idx = search_frame(payload, '7C')
        if (CMD_RSP_HDR ==  payload[idx]) and (idx + 7) <= len(payload):
            status = payload[idx + 6]
            param = payload[(idx + 7): len(payload)]
            ack = True
    return [ack,status,param]

def receive_cmd_response(address):
    ack = False
    status = 0x00
    param = []
    retry = RETRIALS
    while False == ack and 0 < retry:
        retry-=1
        [source_addr, payload] = xbee_obj.xbee_receive_packet()
        if (source_addr == address):
            idx = search_frame(payload, '7C')
            if (CMD_RSP_HDR ==  payload[idx]) and (idx + 7) <= len(payload):
                status = payload[idx + 6]
                param = payload[(idx + 7): len(payload)]
                ack = True
                if True == ack:
                    break
    return [ack, status, param]

def search_frame(payload, frame_hex):
    frame_bytes = bytes.fromhex(frame_hex)
    payload_bytes = bytes(payload)
    index = payload_bytes.find(frame_bytes)
    return index

def wait_fly_pkt(address, xbee_obj):
    while True:
        [source_addr, payload] = xbee_obj.xbee_receive_packet()
        if MIN_FLY_PACKET_LEN <= len(payload):
            fly = [0x46, 0x4C, 0x59]
            if (source_addr == address): 
                idx = search_frame(payload, '7F') 
                if (0x01 == payload[idx + 8]) and (fly == payload[(idx +9):(idx + 12)]):
                    print("Fly Pkt Received !!")
                    break

def send_start_fota(address, xbee_obj):
    cmd = []
    payload = []
    source_address = []
    status = 0
    ret = False
    cmd.append(FOTA_CMD_HDR)
    cmd.append(START_FOTA_MODE_CMD_ID)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd.append(0x00)
    [ret, soruce_address, payload] = xbee_obj.xbee_tx_packet(address, cmd) 
    if True == ret:
        ret = False
        retry = RETRIALS
        if 0 != len(payload):
            [ret, status, param] = resp_packet_decoder(address, source_address, payload)

        while False == ret and 0 < retry:
            retry -=1
            #Receive command response
            [ret, status, param] = receive_cmd_response(address)
            if 0xFF != status:
                ret = False 
                break
    print("Start Fota status",status)
    return ret

def send_read_last_segment(address, xbee_obj):
    cmd = []
    offset = 0
    status = 0
    ret = False
    cmd.append(FOTA_CMD_HDR)
    cmd.append(GET_LAST_FOTA_PGM_SEGMENT)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd.append(0x00)
    ret = False
    for i in range (0, 2):
        [ret, source_address, payload] = xbee_obj.xbee_tx_packet(address, cmd) 
        if 0 != len(payload):
            [ret, status, param] = resp_packet_decoder(address, source_address, payload)
            if 4 == len(param) and (0xFF == status):
                offset = (param[0] << 24) + (param[1] << 16) + (param[2] << 8) + param[3]
                break
            else:
                print("Tx Failed, Retry")
                ret = False
        elif True == ret:
            #Receive command response
            [ret, status, param] = receive_cmd_response(address)
            if 4 == len(param) and (0xFF == status):
                offset = (param[0] << 24) + (param[1] << 16) + (param[2] << 8) + param[3]
                break
            else:
                print("Tx Failed, Retry")
                ret = False
    print("Read Last packet status",status)
    return [ret, offset]

def send_pgm_pkt(address, xbee_obj, pkt_offset, pkt):
    cmd = []
    ret = False
    status = 0
    cmd.append(FOTA_CMD_HDR)
    cmd.append(PGM_FOTA_MEMORY_CMD_ID)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd.append(0x00)
    #Bigendian offset
    cmd.append(0xFF & (pkt_offset >> 24))
    cmd.append(0xFF & (pkt_offset >> 16))
    cmd.append(0xFF & (pkt_offset >> 8))
    cmd.append(0xFF & (pkt_offset >> 0))
    cmd = cmd + list(pkt)
    for i in range (0, 3):
        [ret, source_address, payload] = xbee_obj.xbee_tx_packet(address, cmd) 
        if 0 != len(payload):
            [ret, status, param] = resp_packet_decoder(address, source_address, payload)
            if True == ret:
                if 0xFF != status:
                    ret = False
                break
        elif True == ret:
            #Receive command response
            [ret, status, param] = receive_cmd_response(address)
            if True == ret:
                if 0xFF != status:
                    ret = False
                break
        else:
            print("Tx failed")
        if False == ret: 
            print("Retrying Pgm Pkt")
    print("PGM PKT status",status)
    return ret

def read_current_mainfest(address, xbee_obj):
    cmd = []
    payload = []
    source_address = []
    param = []
    status = 0
    ret = False
    cmd.append(FOTA_CMD_HDR)
    cmd.append(READ_CURRENT_MANIFEST_CMD_ID)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd.append(0x00)
    [ret, source_address, payload] = xbee_obj.xbee_tx_packet(address, cmd)
    if 0 != len(payload):
        [ret, status, param] = resp_packet_decoder(address, source_address, payload)
        if 0xFF != status:
            ret = False
    elif True == ret:
        [ret, status, param] = receive_cmd_response(address)
        if 0xFF != status:
            ret = False 
    else:
            ret = False
    print("Read Manifest status",status) 
    return [ret, param]

def send_store_manifest(address, xbee_obj, manifest):
    cmd = []
    payload = []
    source_address = []
    param = []
    ret = False
    status = 0
    cmd.append(FOTA_CMD_HDR)
    cmd.append(PGM_FOTA_MANIFEST_CMD_ID)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd = cmd + list(manifest)
    [ret, source_address, payload] = xbee_obj.xbee_tx_packet(address, cmd)
    if 0 != len(payload):
        [ret, status, param] = resp_packet_decoder(address, source_address, payload)
        if 0xFF != status:
            ret = False 
    elif True == ret:
        [ret, status, param] = receive_cmd_response(address)
        if 0xFF != status:
            ret = False 
    print("Store Manifest status",status)  
    return ret

def send_reboot(address, xbee_obj):
    cmd = []
    cmd.append(COMM_CMD_HDR)
    cmd.append(REBOOT_CMD)
    cmd.append(0x00)
    cmd.append(0x00)
    cmd.append(0x00)
    ret = xbee_obj.xbee_tx_packet(address, cmd) 
    return ret

com_port = sys.argv[1] # Com port 
update_file = sys.argv[2] # file name
pan_id = int(sys.argv[3], 16) # PAN ID
address = [int(sys.argv[4], 16), int(sys.argv[5], 16), int(sys.argv[6], 16), int(sys.argv[7], 16)]
chunk_size = int(sys.argv[8]) # Chunk Size
fly_wait = int(sys.argv[9]) # Fly wait
start_from_last_segment = bool(int(sys.argv[10])) # Start idx
new_fw_ver = int(0)
#Start Xbee interface
xbee_obj = xbee(com_port)
xbee_obj.xbee_uart_init()

if (chunk_size % 16 == 0):
    with open(update_file, mode="rb") as bin_file:
        fw_update = bin_file.read()
    if 0x01 == fw_update[0]:
        #Extract manifest
        manifest_length = (fw_update[1] << 24) + (fw_update[2] << 16) + (fw_update[3] << 8) + fw_update[4]
        manifest = fw_update[5 : 5 + manifest_length]
        new_fw_ver = manifest[0]
        #Extract Image
        image_offset = 5 + manifest_length
        if 0x02 == fw_update[image_offset]:
            image_length = (fw_update[image_offset + 1] << 24) + (fw_update[image_offset + 2] << 16) + (fw_update[image_offset + 3] << 8) + fw_update[image_offset + 4]
            image_offset = image_offset + 5
            image = fw_update[image_offset : image_offset + image_length]

            # Start Process
            last_offset = 0
            while (True):
                ret = xbee_obj.xbee_set_pan_id(pan_id)
                if True == ret:
                    ret = xbee_obj.xbee_apply_settings()
                    if fly_wait != 0:
					    # Wait fly
                        print("Waiting FLY")
                        wait_fly_pkt(address, xbee_obj)
    
                    [ret, curr_manifest] = read_current_mainfest(address, xbee_obj)
                    if True == ret:
                        curr_fw_ver = curr_manifest[0]
                        if curr_fw_ver == new_fw_ver:
                            ret = False
                            print("ERROR CAN'T UPDATE TO SAME FW VERSION!")
                            break
                    
                    #Send Start FOTA CMD
                    if True == ret:
                        print("Starting FOTA")
                        ret = send_start_fota(address, xbee_obj)
                    if True == ret:
                        print("FOTA Started") 
                        ret = xbee_obj.xbee_set_pan_id(FOTA_MODE_PAN_ID)
                    if True == ret:
                        ret = xbee_obj.xbee_apply_settings()

                    if True == ret:	
                        if True == start_from_last_segment: # Get last offset first	
                            [ret, last_offset] = send_read_last_segment(address, xbee_obj)	
                            if True == ret:	
                                print("Last Segment ", hex(last_offset))

                    if True == ret:
                        if 0 == last_offset: # Program Manifest
                            print("Storing Manifest")
                            time.sleep(1) 
                            curr_manifest_bytes = bytes(curr_manifest)
                            manifest = manifest[:29] + curr_manifest_bytes[29:manifest_length]
                            ret = send_store_manifest(address, xbee_obj, manifest)
                    if True == ret: 
                        #Start programming blocks
                        image_idx = last_offset
                        while image_idx < image_length:
                            #time.sleep(0.1)
                            if (image_idx + chunk_size) > image_length:
                                current_chunk_size = image_length - image_idx
                            else:
                                current_chunk_size = chunk_size
                            pkt = image[image_idx : image_idx + current_chunk_size]
                            print("Pgm pkt @ ", hex(image_idx), " out of ", hex(image_length))
                            ret = send_pgm_pkt(address, xbee_obj, image_idx, pkt)
                            image_idx += current_chunk_size
                            if True == ret:
                                start_from_last_segment = True
                            else:   
                                break

                        if image_idx == image_length:
                            break

            # Image completed, Send Reboot
            print("Sending Reboot")
            ret = send_reboot(address, xbee_obj)
        else:
            print("Wrong File !!!")

    else:
        print("Wrong File !!!")
else:
    print("Chunk Size not multiple of 16")

xbee_obj.xbee_uart_deinit()
