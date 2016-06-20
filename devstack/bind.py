import datetime
import socket
import subprocess
import sys
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

while True:
    with open(sys.argv[1], 'w') as output:
        try:
            s.bind(('', 8088))
            s.close()
            time.sleep(0.5)
        except socket.error as msg:
            output.write(datetime.datetime.utcnow().isoformat() +
                         ' | Bind failed. Error Code : ' + str(msg[0]) +
                         ' Message ' + msg[1] + '\n')
            netstat_info = subprocess.check_output(['sudo', 'netstat', '-anlp'])
            output.write(netstat_info + '\n')
            sys.exit(1)