struct Packet {
};
int reg1_tmp = 0;
void func(struct Packet pkt) {
if (reg1_tmp == 30) {
reg1_tmp = 1;
} else {
reg1_tmp = reg1_tmp + 1; 
}
}
