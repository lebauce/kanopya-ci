#!/usr/bin/python

import pycurl
import curl
cookies = ""

class NetgearUserSession(curl.Curl):
    def login(self, password, cookie=""):
        if cookie:
            self.cookies = cookie

        else:
            self.cookies = ""
            self.post("login.cgi",
                      (("password", "password"),
                       ("rtime", "")))

            cookies = []
            headers = self.header().split("\n")
            for header in headers:
                sep = header.find(" ")
                name, value = header[:sep-1], header[sep+1:]
                if name == "Set-Cookie":
                    cookies.append(value)
        
            self.cookies = "; ".join(cookies)

        if not self.cookies:
            raise Exception("Failed to login")

        self.fakeheaders.append("Cookie: " + self.cookies)

    def create_vlan(self, id):
        print "Creating VLAN", id
        self.post("vlanconfig.cgi",
                  (("action", "1"),
                   ("config", str(id) + ',' + "VLAN" + str(id) + ',')))

    def delete_vlan(self, id):
        print "Deleting VLAN", id
        self.post("vlanconfig.cgi",
                  (("action", "2"),
                   ("config", str(id) + ',' + "VLAN" + str(id) + ',')))

    def get_vlans(self):
        self.get("vlanConfiguration.html")
        import pdb; pdb.set_trace()

    def apply_vlan(self, id):
        print "Applying VLAN"
        self.post("membership.cgi",
                  (("config", str(id) + ',' + "VLAN" + str(id) + ',' + "11110111"),))

    def set_pvid(self, port, id):
        print "Setting VLAN", id, "on port", port
        self.post("setpvid.cgi",
                  (("config", str(port) + ',' + str(id) + ','),))

    def __del__(self):
        self.logout()

    def logout(self):
        self.get("login.html")

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()

    parser.add_option("-p", "--password", dest="password", default="password",
                      help="Password to use for login", metavar="PASSWORD")
    parser.add_option("-s", "--url", dest="server", default="192.168.0.239",
                      help="Netgear", metavar="URL")
    parser.add_option("-c", "--cookie", dest="cookie", default="",
                      help="Authentication cookie", metavar="COOKIE")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="Verbose mode")

    (options, args) = parser.parse_args()

    session = NetgearUserSession(options.server, [ "Keep-Alive: 60", "Connection: keep-alive" ])
    session.login("password")
    # session.get_vlans()
    # session.create_vlan(2)
    # session.delete_vlan(2)
    # session.apply_vlan(1)
    session.set_pvid(5, 3)
