
# Communication Networks: Reliable Transport Layer Protocol

**Assignment 3 | Department of Computer Science**

This project implements a robust **Client-Server Application** designed to demonstrate reliable data transfer mechanisms over a TCP connection. While TCP provides inherent reliability, this application manually implements application-layer flow control and error recovery mechanisms—such as **Sliding Window**, **Go-Back-N**, and **Dynamic Flow Control**—to simulate the internal workings of the Transport Layer.

---

## 🚀 Key Features

* **Persistent Connection (Keep-Alive):** Unlike simple single-file transfer protocols, this implementation maintains an open socket connection. The client can transfer multiple files sequentially without re-establishing the 3-Way Handshake, significantly reducing overhead.
* **Reliable Data Transfer (RDT):** Implements the **Go-Back-N** ARQ protocol. If a packet is lost (simulated via timeout), the client automatically retransmits the entire current window.
* **Sliding Window Mechanism:** Maximizes throughput by allowing multiple unacknowledged packets to be "in-flight" simultaneously, up to a configurable window size.
* **Dynamic Flow Control:** The server can dynamically throttle the client's transmission rate by adjusting the `MAX_MSG_SIZE` in real-time based on sequence logic, simulating network congestion control.
* **Application-Layer Handshake:** Simulates a SYN/ACK connection establishment process before data transmission begins.

---

## 🛠️ Protocol Architecture

The application uses a custom text-based protocol over standard TCP sockets (`SOCK_STREAM`).

### 1. Connection Establishment (Handshake)
Before any data is exchanged, the client and server perform a simulated 3-Way Handshake:
1.  **Client:** Sends `SYN`.
2.  **Server:** Responds with `SYN/ACK`.
3.  **Client:** Sends `ACK` followed by `REQ_MAX_SIZE` to negotiate parameters.
4.  **Server:** Returns the initial buffer size and dynamic capabilities.

### 2. Data Transmission Packet Structure
* **Data Message:** `MSG:<SequenceNumber>|<BinaryData>`
* **Acknowledgment:** `ACK:<SequenceNumber>`
* **Flow Control Update:** `ACK:<SeqNum>|MAX_SIZE:<NewSize>`

### 3. Session Management
* **End of File:** When a file transfer is complete, the client sends a `FIN` flag. The server processes the file, resets sequence counters, and awaits the next file.
* **Teardown:** The connection is only closed when the client explicitly sends a `CLOSE_CONN` command (user inputs 'q').

---

## ⚙️ Configuration

The application can be configured manually via CLI or through a `config.txt` file.

**`config.txt` Format:**
```text
message: "input.txt"
maximum_msg_size: 100
window_size: 5
timeout: 3
dynamic_message_size: True

```

* **`maximum_msg_size`**: Initial payload size in bytes.
* **`window_size`**: Number of allowed unacknowledged packets (N).
* **`timeout`**: Retransmission timer in seconds.
* **`dynamic_message_size`**: Boolean flag. If `True`, the server will actively adjust the packet size during transfer.

---

## 💻 Usage Instructions

### Prerequisites

* Python 3.6 or higher.
* Standard libraries only (`socket`, `threading`, `time`).

### Step 1: Start the Server

Run the server script. You can choose to load settings from `config.txt` or enter them manually.

```bash
python server.py

```

*The server will start listening on port 5555.*

### Step 2: Start the Client

Run the client script in a separate terminal.

```bash
python client.py

```

*The client will initiate the handshake and establish a persistent connection.*

### Step 3: Transfer Files

1. Enter the path of the file you wish to upload (e.g., `input.txt`).
2. The transfer progress will be displayed in real-time (Packets sent, ACKs received).
3. Upon completion, you can enter another filename to transfer immediately without reconnecting.
4. Enter `q` to terminate the connection gracefully.

---

## 🔍 Implementation Details

### The Client (Sender)

* **Threading:** Uses a dedicated background thread to listen for incoming ACKs to prevent blocking the main transmission loop.
* **Locking:** Implements `threading.Lock` to ensure thread-safe access to shared variables (`base`, `next_seq`) between the main sender loop and the ACK listener.
* **Timeout Logic:** Tracks the time of the oldest unacknowledged packet. If the timer expires, the `base` pointer triggers a retransmission loop for the current window.

### The Server (Receiver)

* **Reordering:** Uses a buffer dictionary to store out-of-order packets.
* **In-Order Processing:** Maintains an `expected_sequence` counter. Only packets matching the expected sequence are processed and acknowledged; others are buffered.
* **Stream Parsing:** Manually parses the incoming TCP stream to separate stuck packets (handling TCP stickiness) and extract protocol headers.


```

```
