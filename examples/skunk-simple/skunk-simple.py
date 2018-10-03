from greensim import Simulator, advance, add
from greensim.random import constant, normal, linear, expo, distribution

from itsim import Node, Link, malicious
from itsim import num_bytes
import itsim.software.dhcp as dhcp
from itsim.software.dns import daemon_mdns, daemon_llmnr
from itsim.time import MS, D, H, MIN, next_day, S
from itsim.network import MbPS, GbPS, KbPS


NUM_NODES = 50
FRAC_MDNS = 0.9
NUM_MDNS = int(FRAC_MDNS * NUM_NODES)
NUM_LLMNR = NUM_NODES - NUM_MDNS
DURATION = 5 * D

NIGHT = normal(8.75 * H, 15 * MIN)
BOOT_TO_LOGON = expo(1 * MIN)
WORKDAY = normal(8.5 * H, 30 * MIN)

I_ATTACKED = int(0.37 * NUM_NODES)


@user
def daily_usage(workstation):
    # Midnight: arrive at the office around 8:45.
    advance(next(night))

    # Turn on computer and log in.
    workstation.turn_on()
    advance(next(boot_to_logon))
    workstation.log_in()

    # Work all day.
    advance(next(workday))

    # Turn off computer and redo tomorrow.
    workstation.turn_off()
    midnight = next_day()
    add_at(midnight, daily_usage, workstation)


TIME_TO_ATTACK = bounded(expo(1.5 * D), upper=4.0 * D)
INTERVAL_BEACON = uniform(1.5 * H, 4.5 * H)
LOCATION_MOTHERSHIP = ("mother.ru", 8323)
LEN_BEACON = num_bytes(expo(200), header=128)
LEN_RESPONSE = num_bytes(expo(500), header=128)


@malware
class Backdoor(Malware):

    def __init__(self):
        self.file = File(  # More fields needed.
            "C:\\Program Files (x86)\\Acrobat Reader\\acroread_update.exe",
            size=45898,
            hashes_from="asdf"
        )

    def deploy(self, node):
        self.write_file(node)
        node.autoruns.on_logon(self)
        node.execute(self)

    def run(self, node, thread):
        while True:
            advance(next(INTERVAL_BEACON))
            with node.connect(("mother.ru", 8223)) as socket:
                try:
                    socket.send(next(LEN_BEACON))
                    socket.recv(timeout=5 * S)
                except Socket.Timeout:
                    pass  # Just close and beacon again later.


@attacker
def attack(target, internet):
    # Wait until ready to pounce... and that the user is logged on.
    advance(TIME_TO_ATTACK)
    target.await_login()

    # The user now opens the Zip file it should not have. The backdoor starts a process of its own.
    backdoor = Backdoor().deploy(target)
    internet.resolve(LOCATION_MOTHERSHIP[0], "77.88.55.88")
    internet.serve_at(
        LOCATION_MOTHERSHIP,
        latency=bounded(expo(200.0 * MS), lower=100 * MS),
        bandwidth=normal(1 * MbPS, 100 * KbPS)
        len_response=LEN_RESPONSE
    )


if __name__ == '__main__':
    sim = Simulator()

    local = Link(latency = normal(5 * MS, 1 * MS), bandwidth = constant(1 * GbPS))
    internet = Internet()
    Node(sim, Node.ON) \
        .link(local) \
        .link(internet) \
        .execute(dhcp.Server("192.168.1.0/24"))

    for n in range(1, NUM_NODES):
        ws = Node(sim, Node.OFF).link(local).on_boot(dhcp.Client())
        if n <= NUM_MDNS:
            ws.on_boot(MDNS())
        else:
            ws.on_boot(LLMNR())

        sim.add(daily_usage, ws)

        if n == I_ATTACKED:
            sim.add(attack, ws, internet)

    sim.run(DURATION)
