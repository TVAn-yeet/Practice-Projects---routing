####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json

INF = 16


class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        # TODO
        #   add your own class fields and initialization code here
        
        # port -> (neighbor_addr, cost)
        self.neighbors = {}

        # neighbor_addr -> advertised distance vector
        self.neighbor_vectors = {}

        # destination -> cost
        self.distance_vector = {self.addr: 0}

        # destination -> outgoing port
        self.forwarding_table = {}

    def broadcast_vector(self):
        for port, (neighbor, _) in self.neighbors.items():

            advertised = {}

            for dest, cost in self.distance_vector.items():

                if (
                    dest in self.forwarding_table
                    and self.forwarding_table[dest] == port
                ):
                    advertised[dest] = INF
                else:
                    advertised[dest] = cost

            pkt = Packet(
                Packet.ROUTING,
                self.addr,
                neighbor,
                json.dumps(advertised)
            )

            self.send(port, pkt)

    def recompute(self):

        old_dv = dict(self.distance_vector)
        old_ft = dict(self.forwarding_table)

        new_dv = {self.addr: 0}
        new_ft = {}

        destinations = {self.addr}

        for nbr, vec in self.neighbor_vectors.items():
            destinations.update(vec.keys())

        for _, (nbr, _) in self.neighbors.items():
            destinations.add(nbr)

        for dest in destinations:

            if dest == self.addr:
                continue

            best_cost = INF
            best_port = None

            for port, (nbr, link_cost) in self.neighbors.items():

                if dest == nbr:
                    candidate = link_cost
                else:
                    nbr_cost = self.neighbor_vectors.get(
                        nbr, {}
                    ).get(dest, INF)

                    candidate = min(INF, link_cost + nbr_cost)

                if candidate < best_cost:
                    best_cost = candidate
                    best_port = port

            if best_port is not None:
                new_dv[dest] = best_cost
                new_ft[dest] = best_port

        self.distance_vector = new_dv
        self.forwarding_table = new_ft

        return (
            old_dv != self.distance_vector
            or old_ft != self.forwarding_table
        )

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        # TODO
        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                out_port = self.forwarding_table[packet.dst_addr]
                self.send(out_port, packet)
        else:
            received = json.loads(packet.content)

            changed = (
                self.neighbor_vectors.get(packet.src_addr)
                != received
            )

            if changed:
                self.neighbor_vectors[packet.src_addr] = received
                if self.recompute():
                    self.broadcast_vector()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.neighbors[port] = (endpoint, cost)

        if endpoint not in self.neighbor_vectors:
            self.neighbor_vectors[endpoint] = {}

        if self.recompute():
            self.broadcast_vector()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port not in self.neighbors:
            return

        endpoint, _ = self.neighbors[port]

        del self.neighbors[port]

        if endpoint in self.neighbor_vectors:
            del self.neighbor_vectors[endpoint]

        if self.recompute():
            self.broadcast_vector()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_vector()

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return (
            f"Router {self.addr}\n"
            f"DV={self.distance_vector}\n"
            f"FT={self.forwarding_table}\n"
            f"NBR={self.neighbors}"
        )
