import socket
import time
import threading


def get_config():
    print("\n--- Client Configuration ---")
    #Option to choose between reading from a file and writing by hand
    choice = input("Enter '1' for input1.txt or '2' for manual input: ")
    config = {}
    # if option 1 is chosen, read and parse the configuration file
    if choice == '1':
        try:
            with open('config.txt', 'r') as f:
                for line in f:
                    if ':' in line:
                        k,v = line.strip().split(':', 1)
                        config[k.lower().replace(' ', '_')] = v.strip().replace('"', '')
        except FileNotFoundError:
            print("Config file not found, switching to manual.")
            choice = '2'

    # if option 2 is chosen (or file failed), ask a manual input
    if choice == '2':
        config['message'] = input("Path to input file: ")
        config['window_size'] = int(input("Window size: "))
        config['timeout'] = float(input("Timeout (sec): "))
    else:
        #Default if file exists but keys are missing
        config['message'] = config.get('message','input1.txt')

    #Ensure types are correct
    config['window_size'] = int(config.get('window_size', 5))
    config['timeout'] = float(config.get('timeout', 3))
    return config


def start_client():
    config = get_config()
    #load the file content to memory

    # Connect to server - Persistent Connection
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect(('127.0.0.1', 5555))
        print("[Client] Connected to server.")
    except socket.error:
        print("[Client] Connection failed.")
        return

    # Handshake
    # Send SYN
    client_socket.send("SYN".encode())
    resp = client_socket.recv(1024).decode()
    if "SYN/ACK" in resp:
        print("[Client] Received SYN/ACK. Completing handshake...")
        # Send ACK + request max size
        client_socket.send("ACK".encode())
        time.sleep(0.1) #small delay to prevent packet sticking
        client_socket.send("REQ_MAX_SIZE".encode())

    #get settings
    size_data = client_socket.recv(1024).decode()

    #Clean up buffer if SYN/ACK got stuck to the size message
    if "SYN/ACK" in size_data:
        size_data = size_data.replace("SYN/ACK", "")

    try:
        curr_max_size = int(size_data.split("|")[0])
    except ValueError:
        curr_max_size = 100 #default
    print(f"[Client] Negotiated Max Size: {curr_max_size} bytes")

    # Send Multiple Files
    while True:
        print("\n--- New File Transfer ---")
        file_path = input("Enter file path (or 'q' to quit): ")
        if file_path == 'q':
            client_socket.send("CLOSE_CONN".encode())
            break
        try:
            with open(file_path, 'r') as f:
                full_data = f.read()
        except FileNotFoundError:
            print("Error: File not found. Try again.")
            continue

        #Transfer Variables - Reset variables for NEW file
        base = 0 #tracks the oldest packet that was sent but has not been confirmed by the server yet
        next_seq = 0 #holds the number for the next packet that we are want to send
        packets = [] #saves copies of the data chunks we sent so we can retransmit them if they get lost
        data_ptr = 0 #keeps track of our current position in the file so we know which part to read next

        lock = threading.Lock() #ensures that only one part of the program changes the shared variables at a time to prevent errors
        timer_start = None #records the exact time we started waiting for an acknowledgment to help us detect timeouts
        running = True #keeps the main program loops active and turns false only when the transfer is finished.

        #ACK Listener
        def receive_acks():
            nonlocal base, timer_start, running, curr_max_size
            while running:
                try:
                    client_socket.settimeout(0.5)
                    try:
                        data = client_socket.recv(1024).decode()
                    except socket.timeout:
                        continue

                    if not data: break

                   # Handle stuck ACK (e.g."ACK:1ACK:2")
                    if "ACK:" in data:
                        parts = data.split("ACK:")
                        for part in parts:
                            if not part: continue
                            try:
                            # Parse ACK number
                                ack_val = int(part.split("|")[0])
                            except ValueError: continue

                            with lock:
                                if ack_val >= base:
                                    print(f"[Client] Got ACK:{ack_val}")
                                    base = ack_val+1
                                    #restart timer if there are still unacked packets
                                    timer_start = time.time() if base<next_seq else None
                                #Handle dynamic size update
                                if "MAX_SIZE:" in part:
                                    try:
                                        curr_max_size = int(part.split("MAX_SIZE:")[1])
                                    except: pass
                except:
                    break

        t = threading.Thread(target=receive_acks, daemon=True)
        t.start()
         #Run until all data is sent and all packets are acknowledged
        while base < len(packets) or data_ptr < len(full_data):
            with lock:
                #Send while within window size
                while next_seq < base+config['window_size'] and data_ptr < len(full_data):
                    chunk = full_data[data_ptr: data_ptr+curr_max_size]
                    packets.append(chunk)

                    msg = f"MSG:{next_seq}|{chunk}"
                    client_socket.send(msg.encode())
                    print(f"[Client] Sent M{next_seq} (Size: {len(chunk)})")

                    if base == next_seq: timer_start = time.time()
                    next_seq += 1
                    data_ptr += len(chunk)

                # Timeout:
                if timer_start and (time.time()-timer_start > config['timeout']):
                    print(f"[Client] Timeout! Retransmitting from M{base}")
                    for i in range(base, next_seq):
                        #Retransmit packet i from our storage
                        try:
                            client_socket.send(f"MSG:{i}|{packets[i]}".encode())
                        except IndexError:
                            break
                    timer_start = time.time() #reset timer

            time.sleep(0.1) #Prevent high Processor usage
            #Have we finished reading and dividing the entire original file into packages?
            #Have we received confirmation of all the packages we sent?
            #If so, we can exit from loop:
            if base >= len(packets) and data_ptr >= len(full_data): break

        # File Done - Send FIN
        client_socket.send("FIN".encode())
        print(f"[Client] Finished sending {file_path}")

        # Stop the ACK thread properly
        running = False
        t.join()
        client_socket.settimeout(None)  # Remove timeout for next input

    print("[Client] Transfer Complete.")
    client_socket.close()


if __name__ == "__main__":
    start_client()