struct Packet {
    int pkt_0;
};
void func(struct Packet pkt) {
    pkt.pkt_0 = pkt.pkt_0 + 1;
}
