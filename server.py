import socket

def get_config():
    print("\n--- Server Configuration ---")
    #Option to choose between reading from a file and writing by hand
    choice = input("Enter '1' to read from config.txt or '2' for manual input: ")
    config={}
    # if option 1 is chosen, read and parse the configuration file
    if choice == '1':
        try:
            with open('config.txt','r') as f:
                for line in f:
                    if ':' in line:
                        k,v = line.strip().split(':',1)
                        config[k.lower().replace(' ', '_')]=v.strip().replace('"','')
        except FileNotFoundError:
            print("Config file not found, switching to manual.")
            choice = '2'

    # if option 2 is chosen (or file failed), ask a manual input
    if choice == '2':
        config['maximum_msg_size']= input("Enter Maximum Message Size: ")
        config['dynamic_message_size'] = input("Dynamic Message Size? (True/False): ")

    # Verify the data type (integer for size, and boolean for dynamism)
    config['maximum_msg_size'] = int(config.get('maximum_msg_size', 100))
    config['is_dynamic'] = str(config.get('dynamic_message_size', 'False')).lower()=='true'
    return config


def start_server():
    # Load configuration and set the server socket to listen on port 5555
    config = get_config()
    cur_max_size = config['maximum_msg_size']
    is_dynamic = config['is_dynamic']
    port = 5555


    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #create a new socket using IPv4 (AF_INET) and TCP protocol (SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)# Set socket options to allow the server to restart immediately on the same port to prevent errors
    try:
        srv_sock.bind(('0.0.0.0', 5555)) # Bind the socket to all available network interfaces ('0.0.0.0') on port 5555
        srv_sock.listen(1) # Put the socket into listening mode to wait for incoming connections, '1' specifies the size of the backlog queue (max pending connections)
        print(f"\n[Server] Listening on port {port} (Max Size: {cur_max_size}, Dynamic: {is_dynamic})...")
        #'conn' is the new socket object for sending/receiving data with this specific client.
        #'addr' contains the IP address and port of the connecting client.
        conn, addr = srv_sock.accept()
        print(f"[Server] Connected to {addr}")
    except Exception as e:
        print(f"Socket error: {e}")
        return

    buf = ""   #initialize the buffer to store incoming data strings
    syn_ack_sent = False # Flag to track if the Handshake response(SYN/ACK) has already been sent

    #Creating a reliable connection between the server and the client
    while True:
        try:
            # Read a small chunk of data from the client
            chunk = conn.recv(1024).decode()
            if not chunk: break
            buf += chunk

            #The server receives a connection request and responds with a SYN/ACK
            if "SYN" in buf and not syn_ack_sent:
                conn.send("SYN/ACK".encode())
                syn_ack_sent = True
                buf = buf.replace("SYN", "")

            #Client sends final "ACK" and asks for settings. Server sends the settings.
            if "ACK" in buf and "REQ_MAX_SIZE" in buf:
                resp = f"{cur_max_size}"
                if is_dynamic: resp += "|DYN=True"
                conn.send(resp.encode())
                buf = "" #clear buffer
                break #handshake done, exit loop
        except socket.error:
             break

    #Managing notification receipt
    received_ms = {} #dictionary for storing messages
    exp_seq = 0 #the variable that tracks the next correct sequence we are waiting for
    while True:
        try:
            # Continuously listen for new data chunks coming from the client
            data = conn.recv(4096).decode()
            if not data: break

            if "CLOSE_CONN" in data:
                print("[Server] Client requested close.")
                break

            if "FIN" in data:
                print("\n--- End of File Detected ---")
                # Collect all messages into one complete message and print it
                full_msg = "".join(received_ms[i] for i in sorted(received_ms.keys()))
                print(full_msg)
                print("-----------------------------")

                #Reset variables for the next file
                received_ms = {}
                exp_seq = 0
                data = data.replace("FIN", "")

                if not data: continue

            buf += data

            #Breaking down the buffer into individual messages
            while "MSG:" in buf:
                parts = buf.split("MSG:",2)
                if len(parts)<2: break
                msg_content = parts[1]
                if "|" not in msg_content:
                    break

                # Save the rest of the information in the buffer for further processing
                buf = "MSG:"+parts[2] if len(parts)> 2 else ""

                #Separate the sequence number from the message content
                header, content = msg_content.split("|",1)
                seq_num = int(header)
                print(f"[Server] Received M{seq_num}")
                received_ms[seq_num] = content

                #Check if the received packet is the next expected one
                while exp_seq in received_ms:
                    exp_seq += 1

                # Generate an message (ACK) for the last number received in a valid sequence
                ack_num = exp_seq- 1
                ack_msg = f"ACK:{ack_num}"

                #update the message size dynamically if the condition is true
                if is_dynamic:
                    if ack_num >= 5:
                        cur_max_size = 25
                    ack_msg += f"|MAX_SIZE:{cur_max_size}"

                conn.send(ack_msg.encode())
                print(f"[Server] Sent {ack_msg}")
        except:
            break

    print("\n[Server] Shutting down.")
    conn.close()
    srv_sock.close()


if __name__ == "__main__":
    start_server()