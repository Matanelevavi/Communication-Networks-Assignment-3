import socket


def start_server(config_file='config.txt'):
    # הגדרות ברירת מחדל לשרת (במטלה הערכים נקבעים בעיקר ע"י הלקוח או קובץ, כאן נגדיר קבועים לשם הדוגמה)
    MAX_MSG_SIZE_SERVER = 100
    DYNAMIC_SIZE = False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_port = 12345
    server_socket.bind(('0.0.0.0', server_port))
    server_socket.listen(1)

    print(f"[Server] Listening on port {server_port}...")

    conn, addr = server_socket.accept()
    print(f"[Server] Connection from {addr}")

    # --- שלב 1: לחיצת יד (Handshake) ---
    data = conn.recv(1024).decode()
    if data.strip() == "SIN":
        print("[Server] Received SIN, sending SIN/ACK")
        conn.send("SIN/ACK".encode())
    else:
        print("[Server] Handshake failed: Did not receive SIN")
        conn.close()
        return

    data = conn.recv(1024).decode()
    if data.strip() == "ACK":
        print("[Server] Received ACK. Connection Established.")
    else:
        print("[Server] Handshake failed: Did not receive ACK")
        conn.close()
        return

    # --- שלב 2: משא ומתן על גודל הודעה ---
    data = conn.recv(1024).decode()
    if "REQ_MAX_SIZE" in data:
        # שליחת הגודל המקסימלי שהשרת תומך בו
        response = f"{MAX_MSG_SIZE_SERVER}"
        if DYNAMIC_SIZE:
            response += "|DYN=True"
        conn.send(response.encode())
        print(f"[Server] Sent max size: {MAX_MSG_SIZE_SERVER}")

    # --- שלב 3: קבלת המידע ---
    received_msgs = {}  # מילון לשמירת הודעות: {מספר סידורי: תוכן}
    expected_seq = 0  # המספר הסידורי הבא שאנו מצפים לו ברצף

    while True:
        try:
            data = conn.recv(4096).decode()
            if not data:
                break

            # הנחה: הפורמט הוא "MSG:<seq>|<payload>"
            # ב-TCP ייתכן שנקבל כמה הודעות מחוברות, כאן נניח לצורך הפשטות שהן מגיעות בנפרד או נטפל באחת
            if data.startswith("MSG:"):
                # במקרה של מספר הודעות באותו באפר, ניקח רק את הראשונה לצורך הדגמה פשוטה
                # (במימוש מלא יש לפצל לפי דלימיטר)
                msg_parts = data.split("MSG:")
                for part in msg_parts:
                    if not part: continue

                    if "|" in part:
                        header, content = part.split("|", 1)
                        seq_num = int(header)

                        print(f"[Server] Received Message M{seq_num}")

                        # שמירת ההודעה
                        received_msgs[seq_num] = content

                        # חישוב ה-ACK המצטבר (הכי גבוה ברצף)
                        temp_seq = expected_seq
                        while temp_seq in received_msgs:
                            temp_seq += 1

                        # ה-ACK הוא על האחרון שהתקבל תקין ברצף (temp_seq - 1)
                        # אבל הפרוטוקול המקובל במטלה: ACK מציין מה קיבלנו עד כה
                        ack_num = temp_seq - 1

                        # עדכון הציפייה
                        expected_seq = temp_seq

                        ack_response = f"ACK:{ack_num}"
                        conn.send(ack_response.encode())
                        print(f"[Server] Sent {ack_response}")

        except Exception as e:
            print(f"[Server] Error: {e}")
            break

    conn.close()

    # הדפסת הקובץ המלא בסוף
    full_text = ""
    for i in sorted(received_msgs.keys()):
        full_text += received_msgs[i]
    print("\n--- Full Message Received ---")
    print(full_text)
    print("-----------------------------")


if __name__ == "__main__":
    start_server()