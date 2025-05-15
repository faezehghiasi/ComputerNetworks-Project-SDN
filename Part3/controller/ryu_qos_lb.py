#!/usr/bin/env python3
"""ryu_qos_lb.py – Ryu application for QoS, simple load‑balancing and DoS defence.

* Limits bandwidth of host h1 (10 Mb/s) with an OpenFlow 1.3 meter (ID 2)
* Sends HTTP (TCP/80) down one branch of the tree and SSH (TCP/22) down another
* Implements an L2 learning‑switch so normal traffic is forwarded automatically
* Monitors port statistics every second and, upon detecting a UDP flood
  (rate > 50 Mb/s **and** > 1000 pkts/s), installs a temporary high‑priority rule
  to drop the attack on the ingress port.

Tested with:
  ▸ Mininet 2.3.0d1 + OVS 2.17  ▸ Ryu 4.34  ▸ Python 3.5+
"""

from __future__ import print_function

import collections
import time

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (MAIN_DISPATCHER, CONFIG_DISPATCHER,
                                    DEAD_DISPATCHER, set_ev_cls)
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet
from ryu.ofproto import ofproto_v1_3


class QoSandLB(app_manager.RyuApp):
    """Single‑file Ryu application."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # ---------- user‑tunable constants ----------
    BW_LIMIT_MBPS = 10          # QoS cap for host h1 (Mb/s)
    ROOT_DPID = 1               # dpid of the tree’s root switch
    HTTP_PORT = 80              # service port numbers
    SSH_PORT = 22

    UDP_RATE_THRESHOLD = 50     # Flood‑detection thresholds
    UDP_PKT_THRESHOLD = 1000
    DROP_RULE_IDLE_SECS = 20

    # -------------------------------------------

    def __init__(self, *args, **kwargs):
        super(QoSandLB, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.mac_to_port = {}                       # dpid → {mac:port}
        self.port_stats = collections.defaultdict(dict)  # (dpid,port) → counters
        self.port_rate = collections.defaultdict(dict)   # (dpid,port) → Mb/s
        self.monitor_thread = hub.spawn(self._monitor)

    # ----------------------------------------------------
    # Datapath lifecycle
    # ----------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
            self.logger.info("Register dpid %s", dp.id)
            self._install_meter(dp)
            if dp.id == self.ROOT_DPID:
                self._install_lb_rules(dp)
            # Install default table-miss flow
            parser = dp.ofproto_parser
            ofproto = dp.ofproto
            match = parser.OFPMatch()
            actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                              ofproto.OFPCML_NO_BUFFER)]
            self._add_flow(dp, 0, match, actions)
        elif ev.state == DEAD_DISPATCHER:
            if dp.id in self.datapaths:
                del self.datapaths[dp.id]
                self.logger.info("Unregister dpid %s", dp.id)

    # ----------------------------------------------------
    # QoS: create meter + rule limiting h1’s bandwidth
    # ----------------------------------------------------

    def _install_meter(self, dp):
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        bands = [parser.OFPMeterBandDrop(rate=self.BW_LIMIT_MBPS * 1000,
                                         burst_size=0)]
        mod = parser.OFPMeterMod(datapath=dp,
                                 command=ofp.OFPMC_ADD,
                                 flags=ofp.OFPMF_KBPS,
                                 meter_id=2,
                                 bands=bands)
        dp.send_msg(mod)

        match = parser.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.1")
        actions = []
        inst = [parser.OFPInstructionMeter(2),
                parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=200,
                                table_id=0, match=match, instructions=inst)
        dp.send_msg(mod)

    # ----------------------------------------------------
    # Static load‑balancing rules on root switch
    # ----------------------------------------------------

    def _install_lb_rules(self, dp):
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        ports = sorted(p for p in dp.ports if p != ofp.OFPP_LOCAL)[:2]
        if len(ports) < 2:
            self.logger.warning("Root switch has <2 usable ports — LB disabled")
            return
        http_out, ssh_out = ports[0], ports[1]

        match_http = parser.OFPMatch(eth_type=0x0800, ip_proto=6,
                                      tcp_dst=self.HTTP_PORT)
        actions_http = [parser.OFPActionOutput(http_out)]
        self._add_flow(dp, 100, match_http, actions_http)

        match_ssh = parser.OFPMatch(eth_type=0x0800, ip_proto=6,
                                     tcp_dst=self.SSH_PORT)
        actions_ssh = [parser.OFPActionOutput(ssh_out)]
        self._add_flow(dp, 100, match_ssh, actions_ssh)

        self.logger.info("LB rules: HTTP→port %s, SSH→port %s on dp %s",
                         http_out, ssh_out, dp.id)

    # ----------------------------------------------------
    # Helper to add a single‑table flow‑entry
    # ----------------------------------------------------

    def _add_flow(self, dp, priority, match, actions,
                  idle_timeout=0, hard_timeout=0):
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(dp.ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority,
                                match=match, instructions=inst,
                                idle_timeout=idle_timeout,
                                hard_timeout=hard_timeout)
        dp.send_msg(mod)

    # ----------------------------------------------------
    # Learning‑switch behaviour (table‑miss handler)
    # ----------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        dpid = dp.id
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        out_port = self.mac_to_port[dpid].get(dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(eth_dst=dst)
            self._add_flow(dp, 1, match, actions)

        out = parser.OFPPacketOut(datapath=dp,
                                  buffer_id=ofp.OFP_NO_BUFFER,
                                  in_port=in_port,
                                  actions=actions,
                                  data=msg.data)
        dp.send_msg(out)

    # ----------------------------------------------------
    # Statistics polling & UDP‑flood detection
    # ----------------------------------------------------

    def _monitor(self):
        while True:
            for dp in list(self.datapaths.values()):
                self._request_stats(dp)
            hub.sleep(1)

    def _request_stats(self, dp):
        parser = dp.ofproto_parser
        req = parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY)
        dp.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        now = time.time()
        for stat in body:
            port_no = stat.port_no
            if port_no == ev.msg.datapath.ofproto.OFPP_LOCAL:
                continue
            key = (dpid, port_no)

            prev = self.port_stats.get(key)
            if prev is not None:
                delta_bytes = stat.rx_bytes - prev["bytes"]
                delta_pkts = stat.rx_packets - prev["pkts"]
                delta_t = now - prev["time"]
                if delta_t > 0:
                    rate_mbps = (delta_bytes * 8.0) / (delta_t * 1e6)
                else:
                    rate_mbps = 0.0
                self.port_rate[key] = rate_mbps

                if (rate_mbps > self.UDP_RATE_THRESHOLD and
                        delta_pkts > self.UDP_PKT_THRESHOLD):
                    self.logger.warning("UDP Flood? dp=%s port=%s rate=%.1f Mb/s",
                                        dpid, port_no, rate_mbps)
                    self._install_drop(ev.msg.datapath, port_no)

            self.port_stats[key] = {"bytes": stat.rx_bytes,
                                     "pkts": stat.rx_packets,
                                     "time": now}

    # ----------------------------------------------------
    # Install high‑priority DROP rule for offending port/UDP
    # ----------------------------------------------------

    def _install_drop(self, dp, in_port):
        parser = dp.ofproto_parser
        ofp = dp.ofproto
        match = parser.OFPMatch(in_port=in_port,
                                eth_type=0x0800,
                                ip_proto=17)
        actions = []
        self._add_flow(dp, 65535, match, actions,
                       idle_timeout=self.DROP_RULE_IDLE_SECS)
        self.logger.info("Drop‑rule installed on dp %s port %s (idle %ss)",
                         dp.id, in_port, self.DROP_RULE_IDLE_SECS)

