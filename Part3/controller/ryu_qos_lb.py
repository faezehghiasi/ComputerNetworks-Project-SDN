# ryu_qos_lb.py (Final, Fixed for Meter + TableID)

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import time
import collections

HTTP = 80
SSH = 22
METER_ID = 2

class QoSandLB(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(QoSandLB, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.port_stats = collections.defaultdict(dict)
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def _state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.logger.info("Register dpid {}".format(dp.id))
            self.datapaths[dp.id] = dp
        elif ev.state == ofproto_v1_3.OFPCR_ROLE_SLAVE:
            self.datapaths.pop(dp.id, None)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER,
                                          ofp.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, match, actions)


        bands = [parser.OFPMeterBandDrop(rate=10000, burst_size=1000)]
        meter_mod = parser.OFPMeterMod(datapath=dp, command=ofp.OFPMC_ADD,
                                       flags=ofp.OFPMF_KBPS,
                                       meter_id=METER_ID, bands=bands)
        dp.send_msg(meter_mod)

        # Load Balancing
        if dp.id == 0:
            match = parser.OFPMatch(ip_proto=6, tcp_dst=HTTP)
            actions = [parser.OFPActionOutput(1)]
            self._add_flow(dp, 100, match, actions)

            match = parser.OFPMatch(ip_proto=6, tcp_dst=SSH)
            actions = [parser.OFPActionOutput(2)]
            self._add_flow(dp, 100, match, actions)

        # QoS برای h1 بدون GotoTable
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.1")
        inst = [parser.OFPInstructionMeter(METER_ID)]
        mod = parser.OFPFlowMod(datapath=dp, priority=200,
                                match=match, instructions=inst)
        dp.send_msg(mod)

    def _add_flow(self, dp, priority, match, actions, buffer_id=None):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod_params = dict(datapath=dp, priority=priority,
                          match=match, instructions=inst)
        if buffer_id:
            mod_params["buffer_id"] = buffer_id
        dp.send_msg(parser.OFPFlowMod(**mod_params))

    def _monitor(self):
        while True:
            for dp in list(self.datapaths.values()):
                ofp = dp.ofproto
                parser = dp.ofproto_parser
                req = parser.OFPPortStatsRequest(dp, 0, ofp.OFPP_ANY)
                dp.send_msg(req)
            hub.sleep(1)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply(self, ev):
        dp = ev.msg.datapath
        now = time.time()
        for stat in ev.msg.body:
            port = stat.port_no
            rx = stat.rx_bytes
            tx = stat.tx_bytes
            key = (dp.id, port)
            old = self.port_stats[key]
            if old:
                dt = now - old["time"]
                rate = 8 * (rx - old["rx"]) / dt / 1e6
                if rate > 50 and stat.rx_packets - old["rx_pkts"] > 1000:
                    self.logger.warning("Possible UDP Flood on dp={} port={} rate={:.1f} Mb/s".format(dp.id, port, rate))
                    self._install_drop(dp, port)
            self.port_stats[key] = {"time": now, "rx": rx, "tx": tx,
                                    "rx_pkts": stat.rx_packets}

    def _install_drop(self, dp, ingress_port):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch(in_port=ingress_port, ip_proto=17)
        self._add_flow(dp, 65535, match, [])
        self.logger.info("Installed DROP for UDP on port {}".format(ingress_port))

