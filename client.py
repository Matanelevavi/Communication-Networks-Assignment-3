import socket
import time
import threading


# פונקציה לקריאת קובץ הקונפיגורציה
def get_config():
    config = {}
    try:
        with open('config.txt', 'r') as f:
            for line in f:
                if ':' in line:
                    key, val = line.strip().split(':', 1)
                    val = val.strip().replace('"', '')
                    if val.isdigit():
                        val = int(val)
                    elif val.lower() == 'true':
                        val = True
                    elif val.lower() == 'false':
                        val = False
                    config[key] = val
    except FileNotFoundError:
        print("Config file not found.")
    return config


def start_client():
    config = get_config()

    file_path = config.get('message', 'input.txt')
    window_size = config.get('window_size', 5)
    timeout_val = config.get('timeout', 3)

    # קריאת הקובץ שיש לשלוח
    try:
        with open(file_path, 'r') as f:
            full_data = f.read()
    except Exception as e:
        print(f"[Client] Error reading input file: {e}")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect(('127.0.0.1', 12345))
    except:
        print("[Client] Ensure server is running first.")
        return

    print("[Client] Connected to server.")

    # --- שלב 1: לחיצת יד ---
    print("[Client] Sending SIN...")
    client_socket.send("SIN".encode())

    resp = client_socket.recv(1024).decode()
    if resp.strip() == "SIN/ACK":
        print("[Client] Received SIN/ACK. Sending ACK...")
        client_socket.send("ACK".encode())
    else:
        print("[Client] Handshake failed.")
        return

    # --- שלב 2: בקשת גודל הודעה ---
    client_socket.send("REQ_MAX_SIZE".encode())
    resp = client_socket.recv(1024).decode()

    if "|" in resp:
        max_msg_size = int(resp.split("|")[0])
    else:
        max_msg_size = int(resp)

    print(f"[Client] Negotiated Max Size: {max_msg_size} bytes")

    # --- חלוקה למקטעים ---
    packets = []
    for i in range(0, len(full_data), max_msg_size):
        chunk = full_data[i:i + max_msg_size]
        packets.append(chunk)

    total_packets = len(packets)
    print(f"[Client] Total packets to send: {total_packets}")

    # --- ניהול חלון גלישה ---
    base = 0  # המספר הסידורי של ההודעה הכי ישנה שלא אושרה
    next_seq_num = 0

    lock = threading.Lock()
    timer_start_time = None
    running = True

    # תהליך נפרד לקבלת ACKs מהשרת
    def receive_acks():
        nonlocal base, running, timer_start_time
        while running:
            try:
                ack_data = client_socket.recv(1024).decode()
                if not ack_data: break

                if "ACK:" in ack_data:
                    # ייתכן שיתקבלו כמה ACKs, ניקח את האחרון הרלוונטי
                    parts = ack_data.split("ACK:")
                    last_ack_val = -1
                    for p in parts:
                        if not p: continue
                        # ניקוי זבל אם יש
                        val_str = p.split("|")[0].strip()
                        if val_str.isdigit():
                            last_ack_val = int(val_str)

                    if last_ack_val != -1:
                        with lock:
                            print(f"[Client] Got ACK{last_ack_val}")
                            # אם קיבלנו ACK X, זה אומר שהודעות עד X (כולל) התקבלו.
                            # אז החלון צריך להתקדם ל-X+1
                            if last_ack_val >= base - 1:  # -1 כי ה-base הוא האינדקס הבא לשליחה/אישור
                                # אם last_ack_val הוא 0, זה אומר שקיבלנו את 0. ה-base צריך להיות 1.
                                new_base = last_ack_val + 1
                                if new_base > base:
                                    base = new_base
                                    if base == next_seq_num:
                                        timer_start_time = None  # אין הודעות לא מאושרות
                                    else:
                                        timer_start_time = time.time()  # מתחילים טיימר להודעה הבאה בתור

                    if base >= total_packets:
                        running = False
                        break
            except Exception:
                break

    recv_thread = threading.Thread(target=receive_acks)
    recv_thread.start()

    # --- לולאת השליחה ---
    while base < total_packets and running:

        with lock:
            # שליחת הודעות כל עוד החלון לא מלא
            while next_seq_num < base + window_size and next_seq_num < total_packets:
                payload = packets[next_seq_num]
                msg = f"MSG:{next_seq_num}|{payload}"
                client_socket.send(msg.encode())
                print(f"[Client] Sent M{next_seq_num}")

                if base == next_seq_num:
                    timer_start_time = time.time()  # התחלת טיימר להודעה הראשונה בחלון

                next_seq_num += 1

        # בדיקת Timeout
        with lock:
            if timer_start_time and (time.time() - timer_start_time > timeout_val):
                print("[Client] Timeout! Retransmitting window...")
                # במקרה של Timeout, חוזרים אחורה ל-base ושולחים הכל שוב
                next_seq_num = base
                timer_start_time = time.time()

        time.sleep(0.1)

    running = False
    client_socket.close()
    if recv_thread.is_alive():
        recv_thread.join(timeout=1)
    print("[Client] Finished sending file.")


if __name__ == "__main__":
    start_client()