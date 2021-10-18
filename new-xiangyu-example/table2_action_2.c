struct Packet {
};
int reg2_tmp = 0;
void func(struct Packet pkt) {
if (reg2_tmp == 30) {
reg2_tmp = 1;
} else {
reg2_tmp = reg2_tmp + 1;
}
}
