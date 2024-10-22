import socket
import struct
import dpkt
import platform

class PacketSnifferWindows:
    def __init__(self, ip):
        self.ip = ip
        self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)

    def start_sniffing(self):
        # Bind the socket to the local IP address
        self.sniffer.bind((self.ip, 0))

        # Include IP headers in the capture
        self.sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        # Enable promiscuous mode (Windows specific)
        self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

        print(f"Sniffing on {self.ip} (Windows)")

        try:
            while True:
                # Capture packets
                raw_packet, addr = self.sniffer.recvfrom(65535)

                # Parse the raw packet using dpkt
                ip_packet = dpkt.ip.IP(raw_packet)

                print(f"Source IP: {socket.inet_ntoa(ip_packet.src)} -> Destination IP: {socket.inet_ntoa(ip_packet.dst)}")

                # Check if it's a TCP packet
                if isinstance(ip_packet.data, dpkt.tcp.TCP):
                    tcp = ip_packet.data
                    print(f"  TCP Packet: {tcp.sport} -> {tcp.dport}")

                # Check if it's a UDP packet
                elif isinstance(ip_packet.data, dpkt.udp.UDP):
                    udp = ip_packet.data
                    print(f"  UDP Packet: {udp.sport} -> {udp.dport}")

        except KeyboardInterrupt:
            print("\nPacket sniffing stopped.")
        finally:
            # Disable promiscuous mode
            self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)


class PacketSnifferLinux:
    def __init__(self):
        # Create a raw socket to capture all packets on the network interface
        self.sniffer = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))

    def start_sniffing(self):
        print("Sniffing on all interfaces (Linux)")

        try:
            while True:
                # Capture packets from the network interface
                raw_packet, addr = self.sniffer.recvfrom(65535)

                # Parse the raw packet using dpkt
                eth = dpkt.ethernet.Ethernet(raw_packet)

                # Check if it's an IP packet
                if isinstance(eth.data, dpkt.ip.IP):
                    ip = eth.data
                    print(f"Source IP: {socket.inet_ntoa(ip.src)} -> Destination IP: {socket.inet_ntoa(ip.dst)}")

                    # Check if it's a TCP packet
                    if isinstance(ip.data, dpkt.tcp.TCP):
                        tcp = ip.data
                        print(f"  TCP Packet: {tcp.sport} -> {tcp.dport}")

                    # Check if it's a UDP packet
                    elif isinstance(ip.data, dpkt.udp.UDP):
                        udp = ip.data
                        print(f"  UDP Packet: {udp.sport} -> {udp.dport}")

        except KeyboardInterrupt:
            print("\nPacket sniffing stopped.")


class PacketSniffer:
    def __init__(self):
        self.sniffer = None

        # Detect the platform and choose the appropriate sniffer class
        current_os = platform.system().lower()
        if "windows" in current_os:
            local_ip = self.get_local_ip()
            self.sniffer = PacketSnifferWindows(local_ip)
        elif "linux" in current_os:
            self.sniffer = PacketSnifferLinux()
        else:
            raise NotImplementedError(f"Packet sniffing is not implemented for OS: {current_os}")

    def start(self):
        if self.sniffer:
            self.sniffer.start_sniffing()

    def get_local_ip(self):
        # This function retrieves the local IP address for Windows sniffing
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip


if __name__ == "__main__":
    sniffer = PacketSniffer()
    sniffer.start()
