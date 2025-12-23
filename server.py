import socket


def get_config():
    print("\n--- Server Configuration ---")
    choice = input("Enter '1' to read from config.txt or '2' for manual input: ")
    config = {}
    if choice == '1':
        try:
            with open('config.txt', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, val = line.strip().split(':', 1)
                        config[key.lower().replace(' ', '_')] = val.strip().replace('"', '')
        except:
            choice = '2'

    if choice == '2':
        config['maximum_msg_size'] = input("Enter Maximum Message Size: ")
        config['dynamic_message_size'] = input("Dynamic Message Size? (True/False): ")

    config['maximum_msg_size'] = int(config.get('maximum_msg_size', 100))
    config['is_dynamic'] = str(config.get('dynamic_message_size', 'False')).lower() == 'true'
    return config


def start_server():
    config = get_config()
    max_size = config['maximum_msg_size']
    is_dynamic = config['is_dynamic']
    server_port = 5555

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 5555))
    server_socket.listen(1)
    print(f"\n[Server] Listening on port {server_port} (Max Size: {max_size}, Dynamic: {is_dynamic})...")
    conn, addr = server_socket.accept()
    print(f"[Server] Connected to {addr}")

    buffer = ""
    sin_ack_sent = False

    while True:
        data = conn.recv(1024).decode()
        if not data: break
        buffer += data

        if "SIN" in buffer and not sin_ack_sent:
            conn.send("SIN/ACK".encode())
            sin_ack_sent = True
            buffer = buffer.replace("SIN", "")

        if "ACK" in buffer and "REQ_MAX_SIZE" in buffer:
            resp = f"{max_size}"
            if is_dynamic: resp += "|DYN=True"
            conn.send(resp.encode())
            buffer = ""
            break

    received_msgs = {}
    expected_seq = 0

    while True:
        try:
            data = conn.recv(4096).decode()
            if not data: break
            buffer += data

            while "MSG:" in buffer:
                parts = buffer.split("MSG:", 2)
                if len(parts) < 2: break
                msg_content = parts[1]
                if "|" not in msg_content: break

                buffer = "MSG:" + parts[2] if len(parts) > 2 else ""

                header, content = msg_content.split("|", 1)
                seq_num = int(header)
                print(f"[Server] Received M{seq_num}")
                received_msgs[seq_num] = content

                while expected_seq in received_msgs:
                    expected_seq += 1

                ack_num = expected_seq - 1
                ack_msg = f"ACK:{ack_num}"

                # כאן הגודל נשאר קבוע לפי מה שהגדרת בהתחלה
                if is_dynamic:
                    if ack_num >= 5:
                        max_size = 25
                    ack_msg += f"|MAX_SIZE:{max_size}"

                conn.send(ack_msg.encode())
                print(f"[Server] Sent {ack_msg}")
        except:
            break

    print("\n--- Full Message Received ---")
    print("".join(received_msgs[i] for i in sorted(received_msgs.keys())))
    conn.close()


if __name__ == "__main__":
    start_server()