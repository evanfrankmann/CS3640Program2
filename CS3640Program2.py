import os
import socket
import struct
import time
import select

# Set echo request type to 8
ICMP_ECHO_REQUEST = 8

def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = ord(string[count + 1]) * 256 + ord(string[count])
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2

    if countTo < len(string):
        csum = csum + ord(string[len(string) - 1])
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def sendPingRequest(rawSocket, targetAddress, processId, sequenceNumber):
    # Create the ICMP header with type, code, checksum, process ID, and sequence number
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, 0, processId, sequenceNumber)
    data = struct.pack('!d', time.time())
    # Combine the header and data to create the packet
    packet = header + data
    # Update checksum
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, checksum(packet.decode('latin-1')), processId, sequenceNumber)
    # Update packet
    packet = header + data
    # Use the raw socket to send the echo request to the target address
    # Port number is set to 0 because ICMP ignores port
    rawSocket.sendto(packet, (targetAddress, 0))

def receivePingReply(rawSocket, processId, sequenceNumber, timeout):
    # Store the current time
    startTime = time.time()
    # Loop for the timeout duration
    while time.time() - startTime < timeout:
        # Wait for incoming data on the raw socket
        readable, _, _ = select.select([rawSocket], [], [], timeout - (time.time() - startTime))
        if readable:
            # Receive and store data from the raw socket and sender's address
            packet, address = rawSocket.recvfrom(2048)
            # Extract ICMP header
            icmpHeader = packet[20:28]
            # Unpack the ICMP header fields
            icmpType, _, _, responseProcessId, responseSequenceNumber = struct.unpack('!BBHHH', icmpHeader)
            # Check if the packet is an echo reply and if the process ID and sequence number match expected
            if icmpType == 0 and responseProcessId == processId and responseSequenceNumber == sequenceNumber:
                # Calculate round trip time and return True, the round trip time, and the sender's IP address
                return True, address[0], time.time() - struct.unpack('!d', packet[28:])[0]
    # No ICMP echo reply was received within the timeout duration
    return False, None, None

def ping(host, count=10):
    # Get the current process ID and bitwise AND it with 0xffff to get a 16-bit value
    processId = os.getpid() & 0xffff
    # Try to get the target IP address from the host name
    try:
        targetAddress = socket.gethostbyname(host)
    except socket.gaierror as e:
        print(f"Failed to resolve {host}: {e}")
        return

    # Print the host and target IP address
    print(f"PING {host} ({targetAddress})")

    # Initialize counters for total sent and received packet and total time
    totalSent = 0
    totalReceived = 0
    totalTime = 0

    # Create a raw socket for ICMP
    with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")) as rawSocket:
        # Loop count times to send count ICMP echo requests
        for sequenceNumber in range(1, count + 1):
            # Send an ICMP echo request using the raw socket
            sendPingRequest(rawSocket, targetAddress, processId, sequenceNumber)
            totalSent += 1
            # Receive an ICMP echo reply if any
            success, responseAddress, roundTripTime = receivePingReply(rawSocket, processId, sequenceNumber, 1)
            # If received successfully, increment total received packets, total time, and print the information
            if success:
                totalReceived += 1
                totalTime += roundTripTime
                print(f"{roundTripTime * 1000:.1f} ms from {responseAddress}: icmp_sequence = {sequenceNumber}")
            else:
                # If no echo reply received, print a timeout message with sequence number
                print(f"Request timeout for icmp_sequence {sequenceNumber}")
            # Wait 1 second before sending another echo request
            time.sleep(1)

    # Calculate packet loss as a percentage
    packetLoss = ((totalSent - totalReceived) / totalSent) * 100
    # Calculate the average round trip time
    averageTime = totalTime / totalReceived if totalReceived > 0 else 0

    # Print the ping statistics
    print("{} ping statistics:".format(host))
    print("{} packets transmitted, {} packets received, {:.1f}% packet loss".format(
        totalSent, totalReceived, packetLoss))
    # Print the average round trip time
    print("average round trip = {:.1f} ms".format(
        averageTime * 1000))

if __name__ == "__main__":
    targetHost = "european-union.europa.eu"  
    ping(targetHost)
