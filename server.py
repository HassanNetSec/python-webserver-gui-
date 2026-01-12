import socket
import os
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from datetime import datetime
import webbrowser


def get_content_type(file_path):
    if file_path.endswith(".html"):
        return "text/html"
    if file_path.endswith(".css"):
        return "text/css"
    if file_path.endswith(".js"):
        return "application/javascript"
    if file_path.endswith(".json"):
        return "application/json"
    if file_path.endswith(".png"):
        return "image/png"
    if file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
        return "image/jpeg"
    if file_path.endswith(".gif"):
        return "image/gif"
    return "text/plain"


def send_response(client_socket, status_code, body, content_type="text/html"):
    response_header = f"HTTP/1.1 {status_code}\r\n" \
                      f"Content-Type: {content_type}\r\n" \
                      f"Content-Length: {len(body)}\r\n" \
                      f"Connection: close\r\n\r\n"
    client_socket.send(response_header.encode('utf-8') + body)


def handle_request(client_socket, address, callback):
    try:
        data = client_socket.recv(1024).decode('utf-8')
        if not data:
            return

        request_line = data.split("\r\n")[0]
        method, path, version = request_line.split(" ")

        if path == "/":
            filename = "index.html"
        else:
            filename = path.lstrip("/")

        if os.path.exists(filename) and os.path.isfile(filename):
            with open(filename, "rb") as f:
                content = f.read()
            send_response(client_socket, "200 OK", content, get_content_type(filename))
            callback("success", f"{method} {path}", address[0], len(content))
        else:
            body = b"<html><body><h1>404 Not Found</h1></body></html>"
            send_response(client_socket, "404 Not Found", body)
            callback("error", f"{method} {path}", address[0], 0)

    except Exception as e:
        callback("exception", str(e), address[0], 0)
    finally:
        client_socket.close()


class WebServerGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Professional Web Server")
        self.window.geometry("900x650")
        self.window.resizable(True, True)

        # Color scheme
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.success_color = "#4ec9b0"
        self.error_color = "#f48771"
        self.panel_bg = "#252526"
        self.input_bg = "#3c3c3c"

        self.window.configure(bg=self.bg_color)

        self.server_socket = None
        self.server_thread = None
        self.running = False
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

        self.setup_ui()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def setup_ui(self):
        # Header Frame
        header_frame = tk.Frame(self.window, bg=self.panel_bg, height=80)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_label = tk.Label(header_frame, text="🌐 Web Server Manager",
                               font=("Segoe UI", 20, "bold"),
                               bg=self.panel_bg, fg=self.fg_color)
        title_label.pack(pady=20)

        # Control Panel
        control_frame = tk.Frame(self.window, bg=self.bg_color)
        control_frame.pack(fill=tk.X, padx=20, pady=10)

        # Left side - Server controls
        left_control = tk.Frame(control_frame, bg=self.bg_color)
        left_control.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Port configuration
        port_frame = tk.Frame(left_control, bg=self.bg_color)
        port_frame.pack(side=tk.LEFT, padx=5)

        tk.Label(port_frame, text="Port:", font=("Segoe UI", 10),
                 bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)

        self.port_var = tk.StringVar(value="9999")
        self.port_entry = tk.Entry(port_frame, textvariable=self.port_var,
                                   width=8, font=("Segoe UI", 10),
                                   bg=self.input_bg, fg=self.fg_color,
                                   insertbackground=self.fg_color,
                                   relief=tk.FLAT, bd=0)
        self.port_entry.pack(side=tk.LEFT, padx=5, ipady=5)

        # Start/Stop buttons
        self.start_button = tk.Button(left_control, text="▶ Start Server",
                                      command=self.start_server,
                                      font=("Segoe UI", 10, "bold"),
                                      bg=self.success_color, fg="#000000",
                                      activebackground="#3da58a",
                                      relief=tk.FLAT, bd=0,
                                      padx=20, pady=8, cursor="hand2")
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(left_control, text="⏹ Stop Server",
                                     command=self.stop_server,
                                     font=("Segoe UI", 10, "bold"),
                                     bg=self.error_color, fg="#000000",
                                     activebackground="#d96b5a",
                                     relief=tk.FLAT, bd=0,
                                     padx=20, pady=8, cursor="hand2",
                                     state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Right side - Open browser button
        self.browser_button = tk.Button(control_frame, text="🌍 Open in Browser",
                                        command=self.open_browser,
                                        font=("Segoe UI", 10),
                                        bg=self.accent_color, fg=self.fg_color,
                                        activebackground="#005a9e",
                                        relief=tk.FLAT, bd=0,
                                        padx=20, pady=8, cursor="hand2",
                                        state=tk.DISABLED)
        self.browser_button.pack(side=tk.RIGHT, padx=5)

        # Statistics Panel
        stats_frame = tk.Frame(self.window, bg=self.panel_bg, height=60)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        stats_frame.pack_propagate(False)

        # Status indicator
        status_container = tk.Frame(stats_frame, bg=self.panel_bg)
        status_container.pack(side=tk.LEFT, padx=20, pady=10)

        tk.Label(status_container, text="Status:", font=("Segoe UI", 9),
                 bg=self.panel_bg, fg="#888888").pack(side=tk.LEFT, padx=5)

        self.status_indicator = tk.Label(status_container, text="● Offline",
                                         font=("Segoe UI", 10, "bold"),
                                         bg=self.panel_bg, fg="#666666")
        self.status_indicator.pack(side=tk.LEFT)

        # Request stats
        self.stats_labels = {}
        stats_data = [
            ("Total Requests", "request_count"),
            ("Successful", "success_count"),
            ("Failed", "error_count")
        ]

        for label_text, key in stats_data:
            stat_container = tk.Frame(stats_frame, bg=self.panel_bg)
            stat_container.pack(side=tk.LEFT, padx=20, pady=10)

            tk.Label(stat_container, text=f"{label_text}:",
                     font=("Segoe UI", 9), bg=self.panel_bg,
                     fg="#888888").pack(side=tk.LEFT, padx=5)

            self.stats_labels[key] = tk.Label(stat_container, text="0",
                                              font=("Segoe UI", 10, "bold"),
                                              bg=self.panel_bg, fg=self.fg_color)
            self.stats_labels[key].pack(side=tk.LEFT)

        # Log Panel
        log_container = tk.Frame(self.window, bg=self.bg_color)
        log_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        log_header = tk.Frame(log_container, bg=self.panel_bg, height=35)
        log_header.pack(fill=tk.X)
        log_header.pack_propagate(False)

        tk.Label(log_header, text="📋 Server Logs", font=("Segoe UI", 11, "bold"),
                 bg=self.panel_bg, fg=self.fg_color).pack(side=tk.LEFT, padx=15, pady=8)

        clear_button = tk.Button(log_header, text="Clear Logs",
                                 command=self.clear_logs,
                                 font=("Segoe UI", 9),
                                 bg=self.input_bg, fg=self.fg_color,
                                 activebackground="#4a4a4a",
                                 relief=tk.FLAT, bd=0,
                                 padx=15, pady=4, cursor="hand2")
        clear_button.pack(side=tk.RIGHT, padx=15)

        self.log_text = scrolledtext.ScrolledText(log_container,
                                                  height=15,
                                                  font=("Consolas", 9),
                                                  bg="#1e1e1e",
                                                  fg="#d4d4d4",
                                                  insertbackground=self.fg_color,
                                                  relief=tk.FLAT, bd=0,
                                                  padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure log tags
        self.log_text.tag_config("success", foreground=self.success_color)
        self.log_text.tag_config("error", foreground=self.error_color)
        self.log_text.tag_config("info", foreground=self.accent_color)
        self.log_text.tag_config("timestamp", foreground="#888888")

        # Footer
        footer = tk.Frame(self.window, bg=self.panel_bg, height=30)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        tk.Label(footer, text="Professional Web Server v1.0 | Ready to serve",
                 font=("Segoe UI", 8), bg=self.panel_bg,
                 fg="#888888").pack(pady=7)

    def log_message(self, message, tag="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)

    def update_stats(self):
        self.stats_labels["request_count"].config(text=str(self.request_count))
        self.stats_labels["success_count"].config(text=str(self.success_count))
        self.stats_labels["error_count"].config(text=str(self.error_count))

    def handle_request_callback(self, status, path, ip, size):
        self.request_count += 1

        if status == "success":
            self.success_count += 1
            self.log_message(f"✓ 200 OK - {path} ({size} bytes) → {ip}", "success")
        elif status == "error":
            self.error_count += 1
            self.log_message(f"✗ 404 NOT FOUND - {path} → {ip}", "error")
        else:
            self.log_message(f"⚠ ERROR - {path} → {ip}", "error")

        self.update_stats()

    def start_server(self):
        if self.running:
            return

        try:
            port = int(self.port_var.get())
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', port))
            self.server_socket.listen(5)
            self.running = True

            self.log_message(f"Server started successfully on http://localhost:{port}", "success")
            self.log_message(f"Serving files from: {os.getcwd()}", "info")

            self.status_indicator.config(text="● Online", fg=self.success_color)
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.browser_button.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)

            self.server_thread = threading.Thread(target=self.server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()

        except ValueError as e:
            self.log_message(f"Invalid port: {e}", "error")
        except Exception as e:
            self.log_message(f"Failed to start server: {e}", "error")

    def server_loop(self):
        while self.running:
            try:
                cs, addr = self.server_socket.accept()
                thread = threading.Thread(target=handle_request,
                                          args=(cs, addr, self.handle_request_callback))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    self.log_message(f"Server error: {e}", "error")
                break

    def stop_server(self):
        if not self.running:
            return

        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
                self.log_message("Server stopped successfully", "info")
            except Exception as e:
                self.log_message(f"Error stopping server: {e}", "error")

        self.status_indicator.config(text="● Offline", fg="#666666")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.browser_button.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)

    def open_browser(self):
        if self.running:
            port = self.port_var.get()
            webbrowser.open(f"http://localhost:{port}")
            self.log_message(f"Opening browser at http://localhost:{port}", "info")

    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)
        self.log_message("Logs cleared", "info")

    def on_closing(self):
        if self.running:
            self.stop_server()
        self.window.destroy()


if __name__ == "__main__":
    WebServerGUI()