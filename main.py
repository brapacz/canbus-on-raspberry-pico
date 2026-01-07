from candriver import CanFrame, MCP2515
import time
from machine import unique_id
from can_config import NODE_ID

if __name__ == "__main__":
    print("Hardware ID 0x%s" % unique_id().hex().upper())
    print("Node ID 0x%02X" % NODE_ID)
    
    print("initializing")
    can = MCP2515()
    can.Init(speed="250KBPS")
    print("ready")
    
    hwid_frame = CanFrame(payload=unique_id(), id=(NODE_ID << 4 | 1))
    can.Send(hwid_frame)
    
    uptime_frame = CanFrame(id=(NODE_ID << 4 | 2), payload=[0])
    tick_counter = 0
    
    while True:
        while can.CheckReceiveBuffer():
            frame = can.Receive()
            print("got frame %s" % frame)
            if frame.rtr:
                frame.rtr = False
                frame.payload = [1,2,3]
                frame.dlc=3
                can.Send(frame)
        
        
        can.Send(uptime_frame)
        uptime_frame.payload[0] = (uptime_frame.payload[0]+1)%255
        time.sleep_ms(100)

