import socket
import time
import threading


def get_config():
    print("\n--- Client Configuration ---")
    choice = input("Enter '1' for input.txt or '2' for manual input: ")
    config = {}
    if choice == '1':
        try:
            with open('config.txt', 'r') as f:
                for line in f:
                    if ':' in line:
                        k, v = line.strip().split(':', 1)
                        config[k.lower().replace(' ', '_')] = v.strip().replace('"', '')
        except:
            choice = '2'

    if choice == '2':
        config['message'] = input("Path to input file: ")
        config['window_size'] = int(input("Window size: "))
        config['timeout'] = float(input("Timeout (sec): "))
    else:
        config['window_size'] = int(config.get('window_size', 5))
        config['timeout'] = float(config.get('timeout', 3))
    return config


def start_client():
    config = get_config()
    try:
        with open(config['message'], 'r') as f:
            full_data = f.read()
    except:
        print("Error: Input file not found.")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect(('127.0.0.1', 5555))
        print("[Client] Connected to server.")
    except:
        print("[Client] Connection failed.")
        return

    # Handshake
    client_socket.send("SIN".encode())
    resp = client_socket.recv(1024).decode()
    if "SIN/ACK" in resp:
        print("[Client] Received SIN/ACK. Completing handshake...")
        client_socket.send("ACK".encode())
        time.sleep(0.1)  # השהייה קלה למניעת הדבקת חבילות
        client_socket.send("REQ_MAX_SIZE".encode())

    size_data = client_socket.recv(1024).decode()
    # ניקוי במקרה שקיבלנו שאריות של SIN/ACK בטעות
    if "SIN/ACK" in size_data:
        size_data = size_data.replace("SIN/ACK", "")

    curr_max_size = int(size_data.split("|")[0])
    print(f"[Client] Negotiated Max Size: {curr_max_size} bytes")

    base = 0
    next_seq = 0
    packets = []
    data_ptr = 0
    lock = threading.Lock()
    timer_start = None
    running = True

    def receive_acks():
        nonlocal base, timer_start, running, curr_max_size
        while running:
            try:
                data = client_socket.recv(1024).decode()
                if not data: break
                if "ACK:" in data:
                    # טיפול במקרה של כמה ACKs שנדבקו
                    for part in data.split("ACK:"):
                        if not part: continue
                        ack_val = int(part.split("|")[0])
                        with lock:
                            if ack_val >= base:
                                print(f"[Client] Got ACK:{ack_val}")
                                base = ack_val + 1
                                timer_start = time.time() if base < next_seq else None
                            if "MAX_SIZE:" in part:
                                curr_max_size = int(part.split("MAX_SIZE:")[1])
            except:
                break

    threading.Thread(target=receive_acks, daemon=True).start()

    while base < (len(full_data) / 10) or data_ptr < len(full_data):
        with lock:
            while next_seq < base + config['window_size'] and data_ptr < len(full_data):
                chunk = full_data[data_ptr: data_ptr + curr_max_size]
                packets.append(chunk)
                msg = f"MSG:{next_seq}|{chunk}"
                client_socket.send(msg.encode())
                print(f"[Client] Sent M{next_seq} (Size: {len(chunk)})")
                if base == next_seq: timer_start = time.time()
                next_seq += 1
                data_ptr += len(chunk)

            if timer_start and (time.time() - timer_start > config['timeout']):
                print(f"[Client] Timeout! Retransmitting from M{base}")
                for i in range(base, next_seq):
                    client_socket.send(f"MSG:{i}|{packets[i]}".encode())
                timer_start = time.time()

        time.sleep(0.1)
        if base >= len(packets) and data_ptr >= len(full_data): break

    print("[Client] Transfer Complete.")
    running = False
    client_socket.close()


if __name__ == "__main__":
    start_client()