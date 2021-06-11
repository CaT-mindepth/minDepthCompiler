struct Packet{
    int sport;
    int dport;
    int pkt_0;
    int filter1_idx;
    int filter2_idx;
    int filter3_idx;
};

int state_group_0_state_0 = 0;
int state_group_1_state_0 = 0;
int state_group_2_state_0 = 0;

void func(struct Packet p){
if (state_group_0_state_0!=0&&state_group_1_state_0!=0&&state_group_2_state_0!= 0) {
	p.pkt_0=1;
;}
state_group_0_state_0=1;
state_group_1_state_0=1;
state_group_2_state_0=1;
}