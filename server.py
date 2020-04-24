import socket
import sys
import threading

HOST =                  "10.0.2.2"
PORT =                  3999

CLIENT_KEY =            45328
SERVER_KEY =            54621
MOD_CONST =             65536

MESSAGE_SUFFIX =        b'\a\b'
SERVER_OK =             "200 OK".encode() + MESSAGE_SUFFIX
SERVER_LOGIN_FAILED =   "300 LOGIN FAILED".encode() + MESSAGE_SUFFIX
SERVER_SYNTAX_ERROR =   "301 SYNTAX ERROR".encode() + MESSAGE_SUFFIX
SERVER_LOGIC_ERROR =    "302 LOGIC ERROR".encode() + MESSAGE_SUFFIX
SERVER_MOVE =           "102 MOVE".encode() + MESSAGE_SUFFIX
SERVER_TURN_LEFT =      "103 TURN LEFT".encode() + MESSAGE_SUFFIX
SERVER_TURN_RIGHT =     "104 TURN RIGHT".encode() + MESSAGE_SUFFIX
SERVER_PICK_UP =        "105 GET MESSAGE".encode() + MESSAGE_SUFFIX
SERVER_LOGOUT =         "106 LOGOUT".encode() + MESSAGE_SUFFIX

CLIENT_RECHARGING =     "RECHARGING".encode() + MESSAGE_SUFFIX
CLIENT_FULL_POWER =     "FULL POWER".encode() + MESSAGE_SUFFIX
COMPASS =               ["up", "right", "down", "left"]
STEPS_LIMIT =           50

class ThreadServer(object):
    def __init__(self, conn, addr):
        self.text = ""
        self.conn = conn
        self.addr = addr
        self.position = (0, 0)
        self.direction = "up"
        self.tmp = 0
        self.steps = STEPS_LIMIT
        threading.Thread(target=self.listenToClient, args=()).start()

    def listenToClient(self):
        if not self.authenticate():
            print("SERVER_LOGIN_FAILED", self.conn, self.addr)
            return

        if not self.acquirePosition():
            print("ACQUIRE_POSITION_FAILED", self.conn, self.addr)
            return

        if not self.go_to_goal_corner():
            print("GO_TO_GOAL_FAILED", self.conn, self.addr)
            return
        if not self.find_message():
            print("FIND_MSG_FAILED", self.conn, self.addr)
            return
        print("===============")
        print("SUCCESS! Message:", self.text, self.conn, self.addr, self.position, self.direction)
        print("===============")
        self.conn.send(SERVER_LOGOUT)

    def authenticate(self):
        if not self.hash():
            return False
        server_hash = self.tmp
        server_confirm = bytearray(str((server_hash + SERVER_KEY) % MOD_CONST).encode() + MESSAGE_SUFFIX)
        self.conn.send(server_confirm)
        if not self.check_answer():
            return False
        client_hash = self.tmp
        if client_hash == server_hash:
            self.conn.send(SERVER_OK)
            return True
        else:
            self.conn.send(SERVER_LOGIN_FAILED)
            return False

    def acquirePosition(self):
        self.conn.send(SERVER_TURN_LEFT)
        if not self.parsePosition():
            print("1st_TURN_FAILED", self.conn, self.addr)
            return False
        next_position = self.position
        i = 1
        while next_position == self.position:
            if i == 0:
                self.conn.send(SERVER_TURN_LEFT)
            else:
                self.conn.send(SERVER_MOVE)

            if not self.parsePosition():
                print("WHILE_MOVE_FAILED", self.conn, self.addr, self.position, self.direction, i)
                return False
            i = (i + 1) % 4
        self.direction = ""
        if self.position[0] > next_position[0]:
            self.direction = "left"
        if self.position[0] < next_position[0]:
            self.direction = "right"
        if self.position[1] > next_position[1]:
            self.direction = "down"
        if self.position[1] < next_position[1]:
            self.direction = "up"
        return True

    def go_to_goal_corner(self):
        if abs(self.position[0]) != 2:
            if self.position[0] > 2 or (0 >= self.position[0] > -2):
                while self.direction != "left":
                    self.conn.send(SERVER_TURN_LEFT)
                    if not self.parsePosition():
                        print("GO_TO_GOAL_FAILED", self.conn, self.addr, self.position, self.direction)
                        return False
            else:
                while self.direction != "right":
                    self.conn.send(SERVER_TURN_LEFT)
                    if not self.parsePosition():
                        print("GO_TO_GOAL_FAILED", self.conn, self.addr, self.position, self.direction)
                        return False
            while abs(self.position[0]) != 2:
                self.conn.send(SERVER_MOVE)
                if not self.parsePosition():
                    print("GO_TO_GOAL_FAILED", self.conn, self.addr, self.position, self.direction)
                    return False

        if abs(self.position[1]) != 2:
            if self.position[1] > 2 or (0 >= self.position[1] > -2):
                while self.direction != "down":
                    self.conn.send(SERVER_TURN_LEFT)
                    if not self.parsePosition():
                        print("GO_TO_GOAL_FAILED", self.conn, self.addr, self.position, self.direction)
                        return False
            else:
                while self.direction != "up":
                    self.conn.send(SERVER_TURN_LEFT)
                    if not self.parsePosition():
                        print("GO_TO_GOAL_FAILED", self.conn, self.addr, self.position, self.direction)
                        return False
            while abs(self.position[1]) != 2:
                self.conn.send(SERVER_MOVE)
                if not self.parsePosition():
                    print("GO_TO_GOAL_FAILED", self.conn, self.addr, self.position, self.direction)
                    return False
        return True

    def find_message(self):
        if self.position == (2, 2):
            if not self.read_area("down", "left"):
                return False
        if self.position == (2, -2):
            if not self.read_area("up", "left"):
                return False
        if self.position == (-2, 2):
            if not self.read_area("down", "right"):
                return False
        if self.position == (-2, -2):
            if not self.read_area("up", "right"):
                return False
        return True

    def read_area(self, vertical, horizontal):
        # read rows in in vertical direction
        for height in range(5):
            # set direction
            while self.direction != horizontal:
                self.conn.send(SERVER_TURN_LEFT)
                if not self.parsePosition():
                    print("READ_AREA_ROTATION_FAILED", self.conn, self.addr, self.position, self.direction)
                    return False
            # read 5 fields in row
            for width in range(5):
                self.conn.send(SERVER_PICK_UP)
                if not self.parseMessage():
                    print("READ_AREA_MSG_PARSE_FAILED", self.conn, self.addr, self.position, self.direction,
                          self.text)
                    return False
                if self.text != "":
                    return True
                # move to next row
                if width == 4:
                    if horizontal == "right":
                        if vertical == "down":
                            self.conn.send(SERVER_TURN_RIGHT)
                        else:
                            self.conn.send(SERVER_TURN_LEFT)
                    else:
                        if vertical == "down":
                            self.conn.send(SERVER_TURN_LEFT)
                        else:
                            self.conn.send(SERVER_TURN_RIGHT)
                self.conn.send(SERVER_MOVE)
                if not self.parsePosition():
                    print("READ_AREA_MOVE_FAILED", self.conn, self.addr, self.position, self.direction)
                    return False
            # reading direction changes on new row
            if horizontal == "left":
                horizontal = "right"
            else:
                horizontal = "left"
        print("NO_MESSAGE_FOUND", self.conn, self.addr, self.position, self.direction, self.text)
        return False






    def parsePosition(self):
        message = self.conn.recv(12).decode()
        if message[3] == "-":
            x = message[4]
            if message[6] == "-":
                y = message[7]
            else:
                y = message[6]
        else:
            x = message[3]
            if message[5] == "-":
                y = message[6]
            else:
                y = message[5]
        return (x, y)

    def hash(self):
        message = self.conn.recv(12)
        if len(message) < 3:
            return False
        if not message.decode().endswith(MESSAGE_SUFFIX.decode()):
            return False
        answer = 0
        for i in range(len(message - 2)):
            answer += int.from_bytes(message[i], sys.byteorder)
        self.tmp = (answer * 1000) % MOD_CONST
        return True

    def check_answer(self):
        message = self.conn.recv(7)
        if len(message) < 3:
            return False
        tmp = ""
        for i in range(len(message) - 2):
            tmp += message[i].decode()
        self.tmp = int(tmp)
        return True

    def parseMessage(self):
        pass


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as mySocket:
        mySocket.bind((HOST, PORT))
        mySocket.listen(1)

    while True:
        conn, addr = mySocket.accept()
        ThreadServer(conn, addr)


if __name__ == '__main__':
    main()
