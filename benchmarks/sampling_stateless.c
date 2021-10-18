// Sample every 30th packet in a flow
#define N 30

struct Packet {
  int sample;
};

void func(struct Packet p) {
    p.sample = p.sample + 1;
    p.sample = p.sample + 1;
}
