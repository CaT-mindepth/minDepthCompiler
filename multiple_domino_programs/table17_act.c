struct Packet {
int pkt_15;
int pkt_16;
int pkt_17;
};
void func(struct Packet pkt) {
pkt.pkt_17 = pkt.pkt_16 + pkt.pkt_15;}
